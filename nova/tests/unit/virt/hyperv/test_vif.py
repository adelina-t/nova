# Copyright 2014 Cloudbase Solutions SRL
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

"""
Unit tests for the Hyper-V vif module.
"""

import mock
from oslo.config import cfg

from nova.network import model as network_model
from nova import test
from nova.tests.unit import fake_instance
from nova.virt.hyperv import vif

CONF = cfg.CONF


class TestGetVIFDriver(test.NoDBTestCase):

    def setUp(self):
        patched_utilsfactory = mock.patch.object(vif,
                                                 "utilsfactory")
        patched_utilsfactory.start()
        self.addCleanup(patched_utilsfactory.stop)
        super(TestGetVIFDriver, self).setUp()

    def _test_get_vif_driver(self, expected_driver, vif_type,
                             network_class='nova.network.api.API',
                             expected_exception=None):
        self.flags(network_api_class=network_class)
        if expected_exception:
            self.assertRaises(expected_exception,
                              vif.get_vif_driver,
                              vif_type)
        else:
            actual_class = type(vif.get_vif_driver(vif_type))
            self.assertEqual(expected_driver, actual_class)

    def test_get_vif_driver_neutron(self):
        self._test_get_vif_driver(
            expected_driver=vif.HyperVNeutronVIFDriver,
            vif_type=network_model.VIF_TYPE_OTHER,
            network_class='nova.network.neutronv2.api.API')

    def test_get_vif_driver_nova(self):
        self._test_get_vif_driver(
            expected_driver=vif.HyperVNovaNetworkVIFDriver,
            vif_type=network_model.VIF_TYPE_OTHER,
            network_class='nova.network.api.API')

    def test_get_vif_driver_ovs(self):
        self._test_get_vif_driver(expected_driver=vif.HyperVOVSVIFDriver,
                                  vif_type=network_model.VIF_TYPE_OVS)

    def test_get_vif_driver_invalid_class(self):
        self._test_get_vif_driver(
            expected_driver=None,
            vif_type=network_model.VIF_TYPE_OTHER,
            network_class='fake.driver',
            expected_exception=TypeError)


class TestHyperVOVSVIFDriver(test.NoDBTestCase):

    def setUp(self):
        patched_utilsfactory = mock.patch.object(vif,
                                                 "utilsfactory")
        patched_utilsfactory.start()
        self.addCleanup(patched_utilsfactory.stop)

        self.context = 'fake-context'
        self.instance = fake_instance.fake_instance_obj(self.context)
        self._vif = vif.HyperVOVSVIFDriver()
        self._vif._vmutils = mock.MagicMock()
        self._vif._netutils = mock.MagicMock()

        self._fake_vif = {
            "address": "fake_addr",
            "id": "fake_id",
            "network": {
                "bridge": "fake_bridge",
            }
        }
        super(TestHyperVOVSVIFDriver, self).setUp()

    def test_plug(self):
        mock_get_external_vswitch = self._vif._netutils.get_external_vswitch
        mock_set_nic_connection = self._vif._vmutils.set_nic_connection
        self._vif._netutils.vswitch_port_needed.return_value = False

        self._vif.plug(self.instance, self._fake_vif)

        mock_set_nic_connection.assert_called_once_with(
            self.instance.name,
            self._fake_vif['id'],
            mock_get_external_vswitch())

    @mock.patch('nova.utils.execute')
    def test_post_start(self, mock_execute):
        self._vif.post_start(self.instance, self._fake_vif)
        calls = [
            mock.call('ovs-vsctl', '--timeout=120', '--', '--if-exists',
                      'del-port', 'fake_id', '--', 'add-port',
                      'fake_bridge', 'fake_id',
                      '--', 'set', 'Interface', 'fake_id',
                      'external-ids:iface-id=fake_id',
                      'external-ids:iface-status=active',
                      'external-ids:attached-mac=fake_addr',
                      'external-ids:vm-uuid=%s' % self.instance.uuid)
        ]
        mock_execute.assert_has_calls(calls)

    @mock.patch('nova.utils.execute')
    def test_unplug(self, mock_execute):
        calls = [
            mock.call(
                'ovs-vsctl', '--timeout=120', '--',
                '--if-exists', 'del-port', 'fake_bridge', 'fake_id')
        ]

        self._vif.unplug(self.instance, self._fake_vif)
        mock_execute.assert_has_calls(calls)
