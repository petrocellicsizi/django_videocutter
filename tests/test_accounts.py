# tests/test_accounts.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import Profile
from media_app.models import MediaProject


class AccountsTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        # Client for making requests
        self.client = Client()

    def test_profile_creation(self):
        """Test that a profile is automatically created when a user is created"""
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_register_view(self):
        """Test the register view functionality"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

        # Test user registration
        user_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'complex_password123',
            'password2': 'complex_password123'
        }
        response = self.client.post(reverse('register'), user_data)
        self.assertEqual(response.status_code, 302)  # Check for redirect
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_view(self):
        """Test the login functionality"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

        # Test user login
        login_data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        response = self.client.post(reverse('login'), login_data)
        self.assertEqual(response.status_code, 302)  # Check for redirect

    def test_profile_view_authenticated(self):
        """Test that authenticated users can access the profile page"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_view_unauthenticated(self):
        """Test that unauthenticated users are redirected from the profile page"""
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)  # Check for redirect

    def test_profile_update(self):
        """Test updating user profile information"""
        self.client.login(username='testuser', password='testpassword123')
        update_data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'bio': 'This is my updated bio'
        }
        response = self.client.post(reverse('profile'), update_data)
        self.assertEqual(response.status_code, 302)  # Check for redirect

        # Refresh user from database
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'updateduser')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.profile.bio, 'This is my updated bio')
