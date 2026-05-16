#!/usr/bin/env python3
"""Authentication and authorization smoke tests for PRJ1.

The tests use Flask's in-process test client and a temporary copy of the
SQLite database, so they do not require a running development server and do
not write audit logs into the real application database.
"""

import os
import shutil
import tempfile
import unittest


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DB = os.path.join(ROOT_DIR, "icp_system.db")


class LoginFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="prj1-tests-")
        cls.test_db = os.path.join(cls.temp_dir, "icp_system.db")
        shutil.copy2(SOURCE_DB, cls.test_db)

        import database

        database.DB_PATH = cls.test_db

        import app as app_module

        cls.app_module = app_module
        cls.app = app_module.app
        cls.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        self.client = self.app.test_client()

    def login(self, username="admin", password="admin123"):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )

    def test_unauthenticated_users_are_redirected_to_login(self):
        protected_pages = [
            "/",
            "/dashboard",
            "/controls",
            "/issues",
            "/resources",
            "/audit_logs",
            "/users",
            "/announcements/manage",
            "/controls/manage",
        ]

        for page in protected_pages:
            with self.subTest(page=page):
                response = self.client.get(page, follow_redirects=False)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], "/login")

    def test_admin_can_login_access_core_pages_and_logout(self):
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

        pages = [
            "/",
            "/dashboard",
            "/controls",
            "/issues",
            "/resources",
            "/audit_logs",
            "/users",
            "/announcements/manage",
            "/controls/manage",
        ]

        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page, follow_redirects=False)
                self.assertEqual(response.status_code, 200)

        response = self.client.get("/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

        response = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

    def test_invalid_login_does_not_create_session(self):
        response = self.login("admin", "wrong-password")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

    def test_role_permissions_for_management_pages(self):
        test_users = [
            ("test_audit_manager", "audit_manager", True, True, True),
            ("test_control_owner", "control_owner", False, False, True),
            ("test_tester", "tester", False, False, False),
            ("test_process_owner", "process_owner", False, False, False),
            ("test_approver", "approver", False, False, False),
            ("test_reviewer", "reviewer", False, False, False),
        ]

        for username, role, can_manage_users, can_manage_resources, can_manage_controls in test_users:
            with self.subTest(role=role):
                self.app_module.user_manager.create_user(
                    username=username,
                    password="testpass",
                    role=role,
                    full_name=username,
                )

                client = self.app.test_client()
                login_response = client.post(
                    "/login",
                    data={"username": username, "password": "testpass"},
                    follow_redirects=False,
                )
                self.assertEqual(login_response.status_code, 302)
                self.assertEqual(login_response.headers["Location"], "/")

                users_response = client.get("/users", follow_redirects=False)
                self.assertEqual(users_response.status_code, 200 if can_manage_users else 302)

                resources_response = client.get("/resources/manage", follow_redirects=False)
                self.assertEqual(resources_response.status_code, 200 if can_manage_resources else 302)

                controls_response = client.get("/controls/manage", follow_redirects=False)
                self.assertEqual(controls_response.status_code, 200 if can_manage_controls else 302)


if __name__ == "__main__":
    unittest.main(verbosity=2)
