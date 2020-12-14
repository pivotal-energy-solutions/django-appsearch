# -*- coding: utf-8 -*-
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import re
from urllib.parse import urlencode

from django.apps import apps
from django.test import TestCase
from django.urls import reverse


Company = apps.get_model('company', 'Company')


class SearchTests(TestCase):

    def test_object_contains_data(self):
        """Test a basic contains"""
        self.assertEqual(Company.objects.count(), 0)

        term = "Foobar"
        company = Company.objects.create(name="%s Plumbing" % term)
        self.assertEqual(Company.objects.count(), 1)

        url = reverse('search')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = re.search(r'formChoices\: (\{.*\}),.*setFieldDescription', str(response.content))
        field_dict = eval(data.group(1))
        self.assertEqual(set(field_dict.keys()), {'fields', 'operators'})

        _company = re.search(r'\<option value="(\d+)"\>Company\<\/option\>', str(response.content))
        company_model = _company.group(1)
        self.assertIsNotNone(company_model)

        self.assertIn(company_model, field_dict.get('fields'))
        self.assertIn(company_model, field_dict.get('operators'))

        name_field = next((x for x in field_dict['fields'][company_model] if x[1] == 'Name'))
        self.assertEqual(len(name_field), 3)
        field_id = name_field[0]

        self.assertIn(field_id, field_dict['operators'][company_model])
        self.assertIn('contains', field_dict['operators'][company_model][field_id])
        operator = 'contains'

        data = {
            'form-TOTAL_FORMS': 1,
            'form-INITIAL_FORMS': 0,
            'form-MIN_NUM_FORMS': 0,
            'form-MAX_NUM_FORMS': 10,
            'model': company_model,
            'form-0-type': 'and',
            'form-0-field': field_id,
            'form-0-operator': operator,
            'form-0-term': 'foo',
            'form-0-end_term': None,
        }
        url += "?" + urlencode(data)

        response = self.client.get(url)
        self.assertIn("<h2>1 Compan", str(response.content))
        self.assertIn(company.name, str(response.content))

    def test_object_contains_no_data(self):

        self.assertEqual(Company.objects.count(), 0)
        term = "XYS"
        company = Company.objects.create(name="%s Plumbing" % term)
        self.assertEqual(Company.objects.count(), 1)

        url = reverse('search')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = re.search(r'formChoices\: (\{.*\}),.*setFieldDescription', str(response.content))
        field_dict = eval(data.group(1))
        self.assertEqual(set(field_dict.keys()), {'fields', 'operators'})

        _company = re.search(r'\<option value="(\d+)"\>Company\<\/option\>', str(response.content))
        company_model = _company.group(1)
        self.assertIsNotNone(company_model)

        self.assertIn(company_model, field_dict.get('fields'))
        self.assertIn(company_model, field_dict.get('operators'))

        name_field = next((x for x in field_dict['fields'][company_model] if x[1] == 'Name'))
        self.assertEqual(len(name_field), 3)
        field_id = name_field[0]

        self.assertIn(field_id, field_dict['operators'][company_model])
        self.assertIn('contains', field_dict['operators'][company_model][field_id])
        operator = 'contains'

        data = {
            'form-TOTAL_FORMS': 1,
            'form-INITIAL_FORMS': 0,
            'form-MIN_NUM_FORMS': 0,
            'form-MAX_NUM_FORMS': 10,
            'model': company_model,
            'form-0-type': 'and',
            'form-0-field': field_id,
            'form-0-operator': operator,
            'form-0-term': 'foo',
            'form-0-end_term': None,
        }
        url += "?" + urlencode(data)

        response = self.client.get(url)
        self.assertNotIn("<h2>1 Compan", str(response.content))
        self.assertNotIn(company.name, str(response.content))
