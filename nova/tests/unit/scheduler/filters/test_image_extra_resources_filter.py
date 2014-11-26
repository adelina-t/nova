# Copyright 2014 Cloudbase Solutions Srl
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

from nova.scheduler.filters import image_extra_resources_filter
from nova.scheduler import host_manager
from nova import test


class TestImageExtraResourcesFilter(test.NoDBTestCase):

    FAKE_RESOURCE = 'fake_resource'
    FAKE_REQ_STR = 'fake_string_resource'
    FAKE_REQ_INT = 10

    def setUp(self):
        super(TestImageExtraResourcesFilter, self).setUp()
        self.filt_cls = (
            image_extra_resources_filter.ImageExtraResourcesFilter())

    def _check_satisfies_extra_resources(self, host_extra_resource,
                                         required_resource, expected):
        mock_host = mock.MagicMock(spec=host_manager.HostState)
        mock_host.extra_resources = {self.FAKE_RESOURCE: host_extra_resource}
        img_props = {self.FAKE_RESOURCE: required_resource}

        self.assertEqual(
            expected,
            self.filt_cls._satisfies_extra_resources(mock_host, img_props))

    def test_extra_resources_ignore_unrequired(self):
        self.assertTrue(self.filt_cls._satisfies_extra_resources(
            mock.DEFAULT, {}))

    def test_extra_resource_ignore_property(self):
        mock_host = mock.MagicMock(spec=host_manager.HostState)
        mock_host.extra_resources = {}
        mock_host.hypervisor_type = mock.sentinel.FAKE_HYPERVISOR_TYPE
        img_props = {'hypervisor_type': mock.sentinel.FAKE_HYPERVISOR_TYPE}

        self.assertTrue(
            self.filt_cls._satisfies_extra_resources(mock_host, img_props))

    def test_extra_resources_missing(self):
        self._check_satisfies_extra_resources(
            None, mock.sentinel.FAKE_REQ, False)

    def test_extra_resources_missing_list(self):
        self._check_satisfies_extra_resources(
            [mock.sentinel.FAKE_REQ], self.FAKE_REQ_STR, False)

    def test_extra_resources_found_list(self):
        self._check_satisfies_extra_resources(
            [self.FAKE_REQ_STR], self.FAKE_REQ_STR, True)

    def test_extra_resources_mismatch_str(self):
        self._check_satisfies_extra_resources(
            mock.sentinel.FAKE_REQ, self.FAKE_REQ_STR, False)

    def test_extra_resources_match_str(self):
        self._check_satisfies_extra_resources(
            self.FAKE_REQ_STR, self.FAKE_REQ_STR, True)

    def test_extra_resources_less_int(self):
        self._check_satisfies_extra_resources(
            self.FAKE_REQ_INT, self.FAKE_REQ_INT + 1, False)

    def test_extra_resources_more_int(self):
        self._check_satisfies_extra_resources(
            self.FAKE_REQ_INT, self.FAKE_REQ_INT, True)

    def test_host_passes_no_image(self):
        filter_props = {'request_spec': {'image': {}}}
        self.assertTrue(self.filt_cls.host_passes(mock.DEFAULT, filter_props))

    def test_host_passes_no_image_props(self):
        filter_props = {'request_spec': {'image': {'properties': {}}}}
        self.assertTrue(self.filt_cls.host_passes(mock.DEFAULT, filter_props))

    @mock.patch('nova.scheduler.filters.image_extra_resources_filter.'
                'ImageExtraResourcesFilter._satisfies_extra_resources')
    def test_host_passes_fail(self, mock_satisfies_extra_resources):
        mock_satisfies_extra_resources.return_value = False
        image = {'properties': {self.FAKE_RESOURCE: mock.sentinel.FAKE_VAL}}
        filter_props = {'request_spec': {'image': image}}
        self.assertFalse(self.filt_cls.host_passes(mock.DEFAULT, filter_props))

    @mock.patch('nova.scheduler.filters.image_extra_resources_filter.'
                'ImageExtraResourcesFilter._satisfies_extra_resources')
    def test_host_passes(self, mock_satisfies_extra_resources):
        mock_satisfies_extra_resources.return_value = True
        image = {'properties': {self.FAKE_RESOURCE: mock.sentinel.FAKE_VAL}}
        filter_props = {'request_spec': {'image': image}}
        self.assertTrue(self.filt_cls.host_passes(mock.DEFAULT, filter_props))
