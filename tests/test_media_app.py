# tests/test_media_app.py
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from media_app.models import MediaProject, MediaItem
from media_app.media_processor import process_media_project
from unittest.mock import patch, MagicMock
import tempfile
import os
import shutil
from PIL import Image
import io
import json


class MediaAppTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )

        # Create another user for access control tests
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpassword123'
        )

        # Create a test project
        self.project = MediaProject.objects.create(
            user=self.user,
            title='Test Project',
            description='Test Description',
            type='life_story'
        )

        # Create a project for the other user
        self.other_project = MediaProject.objects.create(
            user=self.other_user,
            title='Other Project',
            description='Other Description',
            type='memory_collection'
        )

        # Create temporary media directory for tests
        self.temp_media_dir = tempfile.mkdtemp()

        # Client for making requests
        self.client = Client()
        self.client.login(username='testuser', password='testpassword123')

    def tearDown(self):
        # Clean up temporary files
        shutil.rmtree(self.temp_media_dir, ignore_errors=True)

        # Clean up any media items
        for item in MediaItem.objects.all():
            if item.file and hasattr(item.file, 'path') and os.path.exists(item.file.path):
                try:
                    os.remove(item.file.path)
                except:
                    pass

    def create_test_image(self, filename='test_image.jpg'):
        """Create a test image file for upload testing"""
        # Create a test image in memory
        image = Image.new('RGB', (100, 100), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile(filename, image_io.read(), content_type='image/jpeg')

    def create_test_video(self, filename='test_video.mp4'):
        """Create a mock video file for upload testing"""
        # This is not a real video, just a simple file that mimics a video upload
        return SimpleUploadedFile(filename, b'file_content', content_type='video/mp4')

    def add_test_media_item(self, project, media_type='image', order=0):
        """Helper method to add a media item to a project"""
        if media_type == 'image':
            file = self.create_test_image()
        else:
            file = self.create_test_video()

        return MediaItem.objects.create(
            project=project,
            file=file,
            media_type=media_type,
            order=order
        )

    # Project Creation and Management Tests
    def test_create_project_success(self):
        """Test creating a new media project with valid data"""
        project_count = MediaProject.objects.count()
        project_data = {
            'title': 'New Test Project',
            'description': 'New Test Description',
            'type': 'event_coverage'
        }
        response = self.client.post(reverse('create_project'), project_data)

        # Check redirect status and message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MediaProject.objects.count(), project_count + 1)

        # Get the newly created project
        new_project = MediaProject.objects.get(title='New Test Project')
        self.assertEqual(new_project.description, 'New Test Description')
        self.assertEqual(new_project.type, 'event_coverage')
        self.assertEqual(new_project.user, self.user)
        self.assertEqual(new_project.status, 'pending')

    def test_create_project_invalid_data(self):
        """Test creating a project with invalid data"""
        project_count = MediaProject.objects.count()
        project_data = {
            'title': '',  # Empty title (required field)
            'description': 'Test Description',
            'type': 'life_story'
        }
        response = self.client.post(reverse('create_project'), project_data)

        # Form should not be valid, so count should not increase
        self.assertEqual(MediaProject.objects.count(), project_count)

        # Check error is shown
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('title', response.context['form'].errors)

    def test_create_project_with_type_param(self):
        """Test that type parameter in URL sets the initial project type"""
        response = self.client.get(reverse('create_project') + '?type=event_coverage')
        self.assertEqual(response.context['form'].initial['type'], 'event_coverage')

    def test_create_project_with_invalid_type_param(self):
        """Test that invalid type parameter doesn't cause errors"""
        response = self.client.get(reverse('create_project') + '?type=invalid_type')
        # Should default to empty or the default value
        self.assertNotIn('type', response.context['form'].initial)

    def test_project_detail_view(self):
        """Test viewing project details"""
        response = self.client.get(reverse('project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')
        self.assertContains(response, 'Test Description')
        self.assertEqual(response.context['project'], self.project)

    def test_update_project_details_success(self):
        """Test successfully updating a project's details"""
        update_data = {
            'title': 'Updated Project',
            'description': 'Updated Description'
        }
        response = self.client.post(reverse('update_project_details', args=[self.project.id]), update_data)
        self.assertEqual(response.status_code, 302)

        # Refresh project from database
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, 'Updated Project')
        self.assertEqual(self.project.description, 'Updated Description')

    def test_update_project_details_invalid(self):
        """Test updating a project with invalid details"""
        original_title = self.project.title
        update_data = {
            'title': '',  # Empty title
            'description': 'Updated Description'
        }
        response = self.client.post(reverse('update_project_details', args=[self.project.id]), update_data)
        self.assertEqual(response.status_code, 302)  # Still redirects

        # Refresh project from database - title should not have changed
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, original_title)

    def test_update_project_type(self):
        """Test updating a project's type"""
        self.assertEqual(self.project.type, 'life_story')

        update_data = {
            'type': 'event_coverage'
        }
        response = self.client.post(reverse('update_project_type', args=[self.project.id]), update_data)
        self.assertEqual(response.status_code, 302)

        # Refresh project from database
        self.project.refresh_from_db()
        self.assertEqual(self.project.type, 'event_coverage')

    def test_update_project_type_invalid(self):
        """Test updating a project with an invalid type"""
        original_type = self.project.type

        update_data = {
            'type': 'invalid_type'
        }
        response = self.client.post(reverse('update_project_type', args=[self.project.id]), update_data)
        self.assertEqual(response.status_code, 302)

        # Refresh project from database - type should not have changed
        self.project.refresh_from_db()
        self.assertEqual(self.project.type, original_type)

    # Media Item Tests
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
        item = MediaItem.objects.filter(project=self.project, media_type='image').first()
        self.assertIsNotNone(item)
        self.assertEqual(item.order, 0)  # Should be the first item

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
        item = MediaItem.objects.filter(project=self.project, media_type='video').first()
        self.assertIsNotNone(item)
        self.assertTrue(item.file.name.endswith('.mp4'))

    def test_add_invalid_media_item(self):
        """Test adding an invalid media item type"""
        # Create a text file (not an image or video)
        invalid_file = SimpleUploadedFile("test.txt", b"invalid content", content_type="text/plain")

        upload_data = {
            'file': invalid_file,
            'media_type': 'image'  # Claiming it's an image when it's not
        }
        response = self.client.post(reverse('project_detail', args=[self.project.id]), upload_data)

        # Should still redirect but with an error
        self.assertEqual(response.status_code, 302)

        # No media items should be created
        self.assertEqual(MediaItem.objects.filter(project=self.project).count(), 0)

    def test_delete_media_item(self):
        """Test deleting a media item from a project"""
        # First create a media item
        media_item = self.add_test_media_item(self.project)
        item_id = media_item.id

        response = self.client.post(reverse('delete_item', args=[item_id]))
        self.assertEqual(response.status_code, 302)  # Check for redirect

        # Check that media item was deleted
        self.assertFalse(MediaItem.objects.filter(id=item_id).exists())

    def test_update_item_order(self):
        """Test reordering media items"""
        # Create several media items
        item1 = self.add_test_media_item(self.project, order=0)
        item2 = self.add_test_media_item(self.project, order=1)
        item3 = self.add_test_media_item(self.project, order=2)

        # Request to update the order
        new_order = [item3.id, item1.id, item2.id]  # Reverse the order
        response = self.client.post(
            reverse('update_item_order'),
            {'item_order[]': new_order},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')

        # Check that orders were updated
        item1.refresh_from_db()
        item2.refresh_from_db()
        item3.refresh_from_db()

        self.assertEqual(item3.order, 0)
        self.assertEqual(item1.order, 1)
        self.assertEqual(item2.order, 2)

    # Project Processing Tests
    @patch('media_app.views.process_media_project')
    def test_process_project(self, mock_process):
        """Test initiating project processing"""
        # Add a media item to the project first
        self.add_test_media_item(self.project)

        response = self.client.post(reverse('process_project', args=[self.project.id]))
        self.assertEqual(response.status_code, 302)  # Check for redirect

        # Check that processing was initiated
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'processing')

        # Check that the process function was called
        # Note: In the real view it's called in a thread, but we're checking it's called
        self.assertTrue(mock_process.called)

    def test_process_empty_project(self):
        """Test that processing an empty project fails appropriately"""
        response = self.client.post(reverse('process_project', args=[self.project.id]))
        self.assertEqual(response.status_code, 302)  # Still redirects

        # Check error message
        storage = response.wsgi_request._messages
        messages = list(storage)
        self.assertTrue(any('Add media' in str(message) for message in messages))

        # Status should not change to processing
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'pending')

    """@patch('media_app.media_processor.upload_file_to_drive')
    @patch('media_app.media_processor.concatenate_videoclips')
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_process_media_project_function(self, mock_concatenate, mock_upload):
        #Test the actual media processing function
        # Setup mocks
        mock_concatenate.return_value = MagicMock()
        mock_concatenate.return_value.write_videofile.return_value = None
        mock_concatenate.return_value.close.return_value = None

        # Mock the drive upload to return a fake link
        mock_upload.return_value = "https://drive.google.com/fake-link"

        # Add media to the project
        self.add_test_media_item(self.project, media_type='image')
        self.add_test_media_item(self.project, media_type='video')

        # Process the project
        result = process_media_project(self.project)

        # Check results
        self.assertTrue(result)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'completed')
        self.assertEqual(self.project.drive_web_view_link, "https://drive.google.com/fake-link")

        # Check that the QR code was generated
        self.assertTrue(self.project.qr_code)"""

    # AJAX and Status Check Tests
    def test_check_project_status_pending(self):
        """Test checking the status of a pending project"""
        self.project.status = 'pending'
        self.project.save()

        response = self.client.get(
            reverse('check_project_status', args=[self.project.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'pending')

    def test_check_project_status_completed(self):
        """Test checking the status of a completed project"""
        # Setup a completed project with output files
        self.project.status = 'completed'
        self.project.drive_web_view_link = "https://drive.google.com/fake-link"
        self.project.output_file = "outputs/test.mp4"
        self.project.qr_code = "qrcodes/test.png"
        self.project.save()

        response = self.client.get(
            reverse('check_project_status', args=[self.project.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['drive_web_view_link'], "https://drive.google.com/fake-link")
        self.assertTrue(data['is_drive_link'])
        self.assertIn('success_message', data)

    # Security and Access Control Tests
    def test_project_access_protection(self):
        """Test that users can only access their own projects"""
        # Try to access the other user's project
        response = self.client.get(reverse('project_detail', args=[self.other_project.id]))
        self.assertEqual(response.status_code, 404)  # Should get 404 Not Found

    def test_media_item_delete_protection(self):
        """Test that users can only delete their own media items"""
        # Create a media item for the other user's project
        other_media_item = self.add_test_media_item(self.other_project)

        # Try to delete it
        response = self.client.post(reverse('delete_item', args=[other_media_item.id]))
        self.assertEqual(response.status_code, 302)  # Redirects with error

        # Item should still exist
        self.assertTrue(MediaItem.objects.filter(id=other_media_item.id).exists())

    def test_reorder_items_protection(self):
        """Test that users can only reorder their own items"""
        # Create items for both projects
        my_item = self.add_test_media_item(self.project)
        other_item = self.add_test_media_item(self.other_project)

        # Try to reorder including the other user's item
        response = self.client.post(
            reverse('update_item_order'),
            {'item_order[]': [other_item.id, my_item.id]},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # Should get a 403 Forbidden
        self.assertEqual(response.status_code, 403)

    def test_process_other_user_project(self):
        """Test that users cannot process other users' projects"""
        response = self.client.post(reverse('process_project', args=[self.other_project.id]))
        self.assertEqual(response.status_code, 404)  # Should get 404 Not Found

        # Project status should not change
        self.other_project.refresh_from_db()
        self.assertEqual(self.other_project.status, 'pending')

    def test_authentication_required(self):
        """Test that unauthenticated users cannot access protected views"""
        # Logout first
        self.client.logout()

        # Try to access various views
        views_to_test = [
            reverse('home'),
            reverse('create_project'),
            reverse('project_detail', args=[self.project.id]),
            reverse('process_project', args=[self.project.id]),
        ]

        for view in views_to_test:
            response = self.client.get(view)
            # Should redirect to login page
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith('/accounts/login/'))


class GoogleDriveUtilsTestCase(TestCase):
    """Tests for Google Drive utilities"""

    @patch('media_app.google_drive_utils.service_account.Credentials.from_service_account_file')
    @patch('media_app.google_drive_utils.build')
    def test_get_drive_service(self, mock_build, mock_credentials):
        """Test creating Google Drive service"""
        from media_app.google_drive_utils import get_drive_service

        # Setup mocks
        mock_credentials.return_value = "fake_credentials"
        mock_build.return_value = "fake_service"

        # Call the function
        service = get_drive_service()

        # Check results
        self.assertEqual(service, "fake_service")
        mock_credentials.assert_called_once()
        mock_build.assert_called_once_with('drive', 'v3', credentials="fake_credentials")

    """@patch('media_app.google_drive_utils.get_drive_service')
    def test_upload_file_to_drive(self, mock_get_service):
        #Test uploading a file to Google Drive
        from media_app.google_drive_utils import upload_file_to_drive

        # Setup mock service and responses
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock the files().create().execute() chain
        mock_file = {'id': 'fake_file_id', 'webViewLink': 'https://drive.google.com/fake'}
        mock_service.files().create().execute.return_value = mock_file

        # Mock the permissions().create().execute() chain
        mock_service.permissions().create().execute.return_value = {}

        # Mock the files().get().execute() chain
        mock_service.files().get().execute.return_value = {'webViewLink': 'https://drive.google.com/fake'}

        # Create a temporary file to upload
        with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
            temp_file.write(b'test content')
            temp_file.flush()

            # Call the function
            result = upload_file_to_drive(temp_file.name, 'test_file.txt')

            # Check results
            self.assertEqual(result, 'https://drive.google.com/fake')
            mock_service.files().create.assert_called_once()
            mock_service.permissions().create.assert_called_once()
            mock_service.files().get.assert_called_once()"""


class QRCodeGenerationTestCase(TestCase):
    """Tests for QR code generation functionality"""

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

        # Setup test client
        self.client = Client()
        self.client.login(username='testuser', password='testpassword123')

        # Create temporary media directory
        self.temp_media_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up temporary files
        shutil.rmtree(self.temp_media_dir, ignore_errors=True)

    @override_settings(MEDIA_ROOT=property(lambda self: self.temp_media_dir))
    def test_generate_qr_code(self):
        #Test generating a QR code for a local video
        from media_app.media_processor import generate_qr_code

        # Create QR code directories
        qr_folder = os.path.join(self.temp_media_dir, 'qrcodes')
        os.makedirs(qr_folder, exist_ok=True)

        # Generate the QR code
        relative_qr_path = 'qrcodes/test_qr.png'
        qr_path = os.path.join(self.temp_media_dir, relative_qr_path)

        result = generate_qr_code(self.project, relative_qr_path, qr_path)

        # Check results
        self.assertTrue(result)
        self.assertTrue(os.path.exists(qr_path))

        # Check that project was updated
        self.project.refresh_from_db()
        self.assertEqual(self.project.qr_code, relative_qr_path)

    @override_settings(MEDIA_ROOT=property(lambda self: self.temp_media_dir))
    def test_generate_qr_code_for_drive(self):
        #Test generating a QR code for a Google Drive link
        from media_app.media_processor import generate_qr_code_for_drive

        # Create QR code directories
        qr_folder = os.path.join(self.temp_media_dir, 'qrcodes')
        os.makedirs(qr_folder, exist_ok=True)

        # Generate the QR code
        relative_qr_path = 'qrcodes/test_drive_qr.png'
        qr_path = os.path.join(self.temp_media_dir, relative_qr_path)
        drive_link = 'https://drive.google.com/fake-link'

        result = generate_qr_code_for_drive(self.project, relative_qr_path, qr_path, drive_link)

        # Check results
        self.assertTrue(result)
        self.assertTrue(os.path.exists(qr_path))

        # Check that project was updated
        self.project.refresh_from_db()
        self.assertEqual(self.project.qr_code, relative_qr_path)

    @patch('media_app.views.update_qr_code')
    def test_update_qr_code_on_status_check(self, mock_update_qr):
        """Test QR code updating when checking project status"""
        mock_update_qr.return_value = True

        # Setup a completed project with local output file
        self.project.status = 'completed'
        self.project.output_file = "outputs/test.mp4"
        self.project.qr_code = "qrcodes/test.png"
        self.project.save()

        # Mock the generate_actual_qr_code function to return PLACEHOLDER_URL
        with patch('media_app.views.generate_actual_qr_code', return_value="PLACEHOLDER_URL"):
            response = self.client.get(
                reverse('check_project_status', args=[self.project.id]),
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )

            # Check that update_qr_code was called
            self.assertTrue(mock_update_qr.called)

            # Check response
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertEqual(data['status'], 'completed')
