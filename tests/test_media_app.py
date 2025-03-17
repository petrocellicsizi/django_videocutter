# tests/test_media_app.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from media_app.models import MediaProject, MediaItem
import tempfile
from PIL import Image
import io


class MediaAppTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )

        # Create a test project
        self.project = MediaProject.objects.create(
            user=self.user,
            title='Test Project',
            description='Test Description',
            type='life_story'
        )

        # Client for making requests
        self.client = Client()
        self.client.login(username='testuser', password='testpassword123')

    def create_test_image(self):
        """Create a test image file for upload testing"""
        # Create a test image in memory
        image = Image.new('RGB', (100, 100), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile('test_image.jpg', image_io.read(), content_type='image/jpeg')

    def create_test_video(self):
        """Create a mock video file for upload testing"""
        # This is not a real video, just a simple file that mimics a video upload
        return SimpleUploadedFile('test_video.mp4', b'file_content', content_type='video/mp4')

    def test_create_project(self):
        """Test creating a new media project"""
        project_data = {
            'title': 'New Test Project',
            'description': 'New Test Description',
            'type': 'event_coverage'
        }
        response = self.client.post(reverse('create_project'), project_data)
        self.assertEqual(response.status_code, 302)  # Check for redirect
        self.assertTrue(MediaProject.objects.filter(title='New Test Project').exists())

    def test_project_detail_view(self):
        """Test viewing project details"""
        response = self.client.get(reverse('project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')

    def test_update_project(self):
        """Test updating a project's details"""
        update_data = {
            'title': 'Updated Project',
            'description': 'Updated Description'
        }
        response = self.client.post(reverse('update_project_details', args=[self.project.id]), update_data)
        self.assertEqual(response.status_code, 302)  # Check for redirect

        # Refresh project from database
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, 'Updated Project')
        self.assertEqual(self.project.description, 'Updated Description')

    def test_add_media_item_image(self):
        """Test adding an image to a project"""
        test_image = self.create_test_image()
        upload_data = {
            'file': test_image,
            'media_type': 'image'
        }
        response = self.client.post(reverse('project_detail', args=[self.project.id]), upload_data)
        self.assertEqual(response.status_code, 302)  # Check for redirect

        # Check that media item was created
        self.assertTrue(MediaItem.objects.filter(project=self.project, media_type='image').exists())

    def test_add_media_item_video(self):
        """Test adding a video to a project"""
        test_video = self.create_test_video()
        upload_data = {
            'file': test_video,
            'media_type': 'video'
        }
        response = self.client.post(reverse('project_detail', args=[self.project.id]), upload_data)
        self.assertEqual(response.status_code, 302)  # Check for redirect

        # Check that media item was created
        self.assertTrue(MediaItem.objects.filter(project=self.project, media_type='video').exists())

    def test_delete_media_item(self):
        """Test deleting a media item from a project"""
        # First create a media item
        media_item = MediaItem.objects.create(
            project=self.project,
            media_type='image',
            file='test_path.jpg',
            order=1
        )

        response = self.client.post(reverse('delete_item', args=[media_item.id]))
        self.assertEqual(response.status_code, 302)  # Check for redirect

        # Check that media item was deleted
        self.assertFalse(MediaItem.objects.filter(id=media_item.id).exists())

    def test_process_project(self):
        """Test processing a project"""
        response = self.client.post(reverse('process_project', args=[self.project.id]))
        self.assertEqual(response.status_code, 302)  # Check for redirect

    def test_project_access_protection(self):
        """Test that users can only access their own projects"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpassword123'
        )

        # Create a project for the other user
        other_project = MediaProject.objects.create(
            user=other_user,
            title='Other Project',
            description='Other Description',
            type='memory_collection'
        )

        # Try to access the other user's project
        response = self.client.get(reverse('project_detail', args=[other_project.id]))
        # Should get a 403 Forbidden or a 404 Not Found, depending on implementation
        self.assertIn(response.status_code, [403, 404])