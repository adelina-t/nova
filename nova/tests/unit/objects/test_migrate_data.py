#    Copyright 2015 Red Hat, Inc.
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

from nova import objects
from nova.objects import migrate_data
from nova.tests.unit.objects import test_objects


class _TestLiveMigrateData(object):
    def test_to_legacy_dict(self):
        obj = migrate_data.LiveMigrateData(is_volume_backed=False)
        self.assertEqual({'is_volume_backed': False},
                         obj.to_legacy_dict())

    def test_from_legacy_dict(self):
        obj = migrate_data.LiveMigrateData()
        obj.from_legacy_dict({'is_volume_backed': False, 'ignore': 'foo'})
        self.assertEqual(False, obj.is_volume_backed)

    def test_from_legacy_dict_migration(self):
        migration = objects.Migration()
        obj = migrate_data.LiveMigrateData()
        obj.from_legacy_dict({'is_volume_backed': False, 'ignore': 'foo',
                              'migration': migration})
        self.assertEqual(False, obj.is_volume_backed)
        self.assertIsInstance(obj.migration, objects.Migration)

    def test_legacy_with_pre_live_migration_result(self):
        obj = migrate_data.LiveMigrateData(is_volume_backed=False)
        self.assertEqual({'pre_live_migration_result': {},
                          'is_volume_backed': False},
                         obj.to_legacy_dict(pre_migration_result=True))


class TestLiveMigrateData(test_objects._LocalTest,
                          _TestLiveMigrateData):
    pass


class TestRemoteLiveMigrateData(test_objects._RemoteTest,
                                _TestLiveMigrateData):
    pass


class _TestLibvirtLiveMigrateData(object):
    def test_bdm_to_disk_info(self):
        obj = migrate_data.LibvirtLiveMigrateBDMInfo(
            serial='foo', bus='scsi', dev='sda', type='disk')
        expected_info = {
            'dev': 'sda',
            'bus': 'scsi',
            'type': 'disk',
        }
        self.assertEqual(expected_info, obj.as_disk_info())
        obj.format = 'raw'
        obj.boot_index = 1
        expected_info['format'] = 'raw'
        expected_info['boot_index'] = '1'
        self.assertEqual(expected_info, obj.as_disk_info())

    def test_to_legacy_dict(self):
        obj = migrate_data.LibvirtLiveMigrateData(
            is_volume_backed=False,
            filename='foo',
            image_type='rbd',
            block_migration=False,
            disk_over_commit=False,
            disk_available_mb=123,
            is_shared_instance_path=False,
            is_shared_block_storage=False,
            instance_relative_path='foo/bar')
        expected = {
            'is_volume_backed': False,
            'filename': 'foo',
            'image_type': 'rbd',
            'block_migration': False,
            'disk_over_commit': False,
            'disk_available_mb': 123,
            'is_shared_instance_path': False,
            'is_shared_block_storage': False,
            'instance_relative_path': 'foo/bar',
        }
        self.assertEqual(expected, obj.to_legacy_dict())

    def test_from_legacy_dict(self):
        obj = migrate_data.LibvirtLiveMigrateData(
            is_volume_backed=False,
            filename='foo',
            image_type='rbd',
            block_migration=False,
            disk_over_commit=False,
            disk_available_mb=123,
            is_shared_instance_path=False,
            is_shared_block_storage=False,
            instance_relative_path='foo/bar')
        legacy = obj.to_legacy_dict()
        legacy['ignore_this_thing'] = True
        obj2 = migrate_data.LibvirtLiveMigrateData()
        obj2.from_legacy_dict(legacy)
        self.assertEqual(obj.filename, obj2.filename)

    def test_to_legacy_dict_with_pre_result(self):
        test_bdmi = migrate_data.LibvirtLiveMigrateBDMInfo(
            serial='123',
            bus='scsi',
            dev='/dev/sda',
            type='disk',
            format='qcow2',
            boot_index=1,
            connection_info='myinfo')
        obj = migrate_data.LibvirtLiveMigrateData(
            is_volume_backed=False,
            filename='foo',
            image_type='rbd',
            block_migration=False,
            disk_over_commit=False,
            disk_available_mb=123,
            is_shared_instance_path=False,
            is_shared_block_storage=False,
            instance_relative_path='foo/bar',
            graphics_listen_addr_vnc='127.0.0.1',
            serial_listen_addr='127.0.0.1',
            bdms=[test_bdmi])
        legacy = obj.to_legacy_dict(pre_migration_result=True)
        self.assertIn('pre_live_migration_result', legacy)
        expected = {
            'graphics_listen_addrs': {'vnc': '127.0.0.1',
                                      'spice': None},
            'serial_listen_addr': '127.0.0.1',
            'volume': {
                '123': {
                    'connection_info': 'myinfo',
                    'disk_info': {
                        'bus': 'scsi',
                        'dev': '/dev/sda',
                        'type': 'disk',
                        'format': 'qcow2',
                        'boot_index': '1',
                    }
                }
            }
        }
        self.assertEqual(expected, legacy['pre_live_migration_result'])

    def test_from_legacy_with_pre_result(self):
        test_bdmi = migrate_data.LibvirtLiveMigrateBDMInfo(
            serial='123',
            bus='scsi',
            dev='/dev/sda',
            type='disk',
            format='qcow2',
            boot_index=1,
            connection_info='myinfo')
        obj = migrate_data.LibvirtLiveMigrateData(
            is_volume_backed=False,
            filename='foo',
            image_type='rbd',
            block_migration=False,
            disk_over_commit=False,
            disk_available_mb=123,
            is_shared_instance_path=False,
            is_shared_block_storage=False,
            instance_relative_path='foo/bar',
            graphics_listen_addrs={'vnc': '127.0.0.1'},
            serial_listen_addr='127.0.0.1',
            bdms=[test_bdmi])
        obj2 = migrate_data.LibvirtLiveMigrateData()
        obj2.from_legacy_dict(obj.to_legacy_dict())
        self.assertEqual(obj.to_legacy_dict(),
                         obj2.to_legacy_dict())


class TestLibvirtLiveMigrateData(test_objects._LocalTest,
                                 _TestLibvirtLiveMigrateData):
    pass


class TestRemoteLibvirtLiveMigrateData(test_objects._RemoteTest,
                                       _TestLibvirtLiveMigrateData):
    pass


class _TestHyperVLiveMigrateData(object):
    def test_to_legacy_dict(self):
        obj = migrate_data.LiveMigrateData(is_volume_backed=False,
                                           is_shared_instance_path=True)
        self.assertEqual({'is_volume_backed': False,
                          'is_shared_instance_path': True},
                         obj.to_legacy_dict())

    def test_from_legacy_dict(self):
        obj = migrate_data.LiveMigrateData()
        obj.from_legacy_dict({'is_volume_backed': False,
                              'is_shared_instance_path': True,
                              'ignore': 'foo'})
        self.assertEqual(False, obj.is_volume_backed)
        self.assertEqual(True, obj.is_shared_instance_path)

    def test_from_legacy_dict_migration(self):
        migration = objects.Migration()
        obj = migrate_data.LiveMigrateData()
        obj.from_legacy_dict({'is_volume_backed': False,
                              'is_shared_instance_path': False,
                              'ignore': 'foo',
                              'migration': migration})
        self.assertEqual(False, obj.is_volume_backed)
        self.assertIsInstance(obj.migration, objects.Migration)

    def test_legacy_with_pre_live_migration_result(self):
        obj = migrate_data.LiveMigrateData(is_volume_backed=False,
                                           is_shared_instance_path=False)
        self.assertEqual({'pre_live_migration_result': {},
                          'is_shared_instance_path': False,
                          'is_volume_backed': False},
                         obj.to_legacy_dict(pre_migration_result=True))


class TestHyperVLiveMigrateData(test_objects._LocalTest,
                                _TestLiveMigrateData):
    pass


class TestRemoteHyperVLiveMigrateData(test_objects._RemoteTest,
                                      _TestLiveMigrateData):
    pass
