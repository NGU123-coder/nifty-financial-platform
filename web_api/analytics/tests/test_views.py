from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import User
from analytics.models import Sector, Company

class APITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')
        
        self.sector = Sector.objects.create(sector_name="Technology")
        self.company = Company.objects.create(
            symbol="TEST", 
            company_name="Test Company", 
            sector=self.sector,
            industry="Software"
        )

    def test_get_sectors(self):
        url = reverse('sector-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['sector_name'], "Technology")

    def test_get_companies(self):
        url = reverse('company-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['symbol'], "TEST")

    def test_company_search(self):
        url = reverse('company-list') + '?search=TEST'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
