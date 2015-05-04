# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

from nova.network import net_common
from nova.network import ovs_utils
from nova import test
from nova import utils


class OVSUtilsTestCase(test.NoDBTestCase):

    def _create_ovs_vif_port(self, calls):
        with mock.patch.object(utils, 'execute', return_value=('', '')) as ex:
            ovs_utils.create_ovs_vif_port('fake-bridge', 'fake-dev',
                                          'fake-iface-id', 'fake-mac',
                                          'fake-instance-uuid')
            ex.assert_has_calls(calls)

    def _delete_ovs_vif_port(self, calls):
        with mock.patch.object(utils, 'execute', return_value=('', ' ')) as ex:
            with mock.patch.object(net_common, 'device_exists',
                                   return_value=True):
                ovs_utils.delete_ovs_vif_port('fake-bridge', 'fake-dev')
                ex.assert_has_calls(calls)

    def test_create_ovs_vif_port(self):
        calls = [
                mock.call('ovs-vsctl', '--timeout=120', '--', '--if-exists',
                          'del-port', 'fake-dev', '--', 'add-port',
                          'fake-bridge', 'fake-dev',
                          '--', 'set', 'Interface', 'fake-dev',
                          'external-ids:iface-id=fake-iface-id',
                          'external-ids:iface-status=active',
                          'external-ids:attached-mac=fake-mac',
                          'external-ids:vm-uuid=fake-instance-uuid',
                          run_as_root=True)
                ]
        self._create_ovs_vif_port(calls)

    def test_create_ovs_vif_port_with_mtu(self):
        self.flags(network_device_mtu=10000)
        calls = [
                mock.call('ovs-vsctl', '--timeout=120', '--', '--if-exists',
                          'del-port', 'fake-dev', '--', 'add-port',
                          'fake-bridge', 'fake-dev',
                          '--', 'set', 'Interface', 'fake-dev',
                          'external-ids:iface-id=fake-iface-id',
                          'external-ids:iface-status=active',
                          'external-ids:attached-mac=fake-mac',
                          'external-ids:vm-uuid=fake-instance-uuid',
                          run_as_root=True),
                mock.call('ip', 'link', 'set', 'fake-dev', 'mtu',
                          10000, run_as_root=True,
                          check_exit_code=[0, 2, 254])
                ]
        self._create_ovs_vif_port(calls)

    def test_delete_ovs_vif_port(self):
        calls = [mock.call('ovs-vsctl', '--timeout=120', '--', '--if-exists',
                           'del-port', 'fake-bridge', 'fake-dev',
                            run_as_root=True)
                ]
        self._delete_ovs_vif_port(calls)

    def test_delete_ovs_vif_port_delete_net_dev(self):
        calls = [mock.call('ovs-vsctl', '--timeout=120', '--', '--if-exists',
                           'del-port', 'fake-bridge', 'fake-dev',
                            run_as_root=True),
                 mock.call('ip', 'link', 'delete', 'fake-dev',
                          run_as_root=True, check_exit_code=[0, 2, 254])
                ]
        self._delete_ovs_vif_port(calls)

    def test_ovs_set_vhostuser_type(self):
        calls = [
                 mock.call('ovs-vsctl', '--timeout=120', '--', 'set',
                           'Interface', 'fake-dev', 'type=dpdkvhostuser',
                           run_as_root=True)
                 ]
        with mock.patch.object(utils, 'execute', return_value=('', '')) as ex:
            ovs_utils.ovs_set_vhostuser_port_type('fake-dev')
            ex.assert_has_calls(calls)

    def _test_check_bridge_has_dev(self, dev, expected_value, calls):
        with mock.patch.object(utils, 'execute',
            return_value=('fake-dev\nfake-dev1', '  ')) as ex:
            ret = ovs_utils.check_bridge_has_dev('fake-bridge', dev)
            self.assertEqual(ret, expected_value)
            ex.assert_has_calls(calls)

    def test_check_bridge_has_dev_true(self):
        calls = [mock.call('ovs-vsctl', '--timeout=120', '--', 'list-ports',
                           'fake-bridge', run_as_root=True)]
        self._test_check_bridge_has_dev(dev='fake-dev1', expected_value=True,
                                      calls=calls)

    def test_check_bridge_has_dev_false(self):
        calls = [mock.call('ovs-vsctl', '--timeout=120', '--', 'list-ports',
                           'fake-bridge', run_as_root=True)]
        self._test_check_bridge_has_dev(dev='fake-dev2', expected_value=False,
                                      calls=calls)
