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

from nova import exception
from nova.tests.unit.virt.hyperv import test_base
from nova.virt.hyperv import namedpipe
from nova.virt.hyperv import pathutils
from nova.virt.hyperv import serialconsolehandler
from nova.virt.hyperv import serialproxy
from nova.virt.hyperv import vmutils


class SerialConsoleHandlerTestCase(test_base.HyperVBaseTestCase):
    _FAKE_INSTANCE_NAME = 'fake_instance_name'

    def setUp(self):
        super(SerialConsoleHandlerTestCase, self).setUp()
        self._consolehandler = serialconsolehandler.SerialConsoleHandler(
            self._FAKE_INSTANCE_NAME)

    @mock.patch.object(serialconsolehandler.SerialConsoleHandler,
                       '_setup_handlers')
    def test_start_handler(self, mock_setup_handlers):
        mock_serial_proxy = mock.Mock()
        mock_pipe_handler = mock.Mock()

        self._consolehandler._serial_proxy = mock_serial_proxy
        self._consolehandler._named_pipe_handler = mock_pipe_handler

        self._consolehandler.start()

        mock_setup_handlers.assert_called_once_with()
        mock_serial_proxy.start.assert_called_once_with()
        mock_pipe_handler.start.assert_called_once_with()

    @mock.patch('nova.console.serial.release_port')
    def test_stop_handler(self, mock_release_port):
        mock_serial_proxy = mock.Mock()
        mock_pipe_handler = mock.Mock()
        self._consolehandler._serial_proxy = mock_serial_proxy
        self._consolehandler._named_pipe_handler = mock_pipe_handler
        self._consolehandler._listen_host = mock.sentinel.host
        self._consolehandler._listen_port = mock.sentinel.port

        self._consolehandler.stop()

        mock_serial_proxy.stop.assert_called_once_with()
        mock_pipe_handler.stop.assert_called_once_with()
        mock_release_port.assert_called_once_with(mock.sentinel.host,
                                                  mock.sentinel.port)

    @mock.patch.object(vmutils.VMUtils, 'get_vm_serial_port_connection')
    @mock.patch.object(serialproxy, 'SerialProxy')
    @mock.patch.object(namedpipe, 'NamedPipeHandler')
    @mock.patch('nova.console.serial.acquire_port')
    @mock.patch.object(pathutils.PathUtils, 'get_vm_console_log_paths')
    def _test_setup_handlers(self, mock_get_log_paths,
                             mock_acquire_port,
                             mock_pipe_handler_class,
                             mock_serial_proxy_class,
                             mock_get_serial_port,
                             serial_console_enabled=True):
        mock_get_log_paths.return_value = [mock.sentinel.log_path]
        mock_get_serial_port.return_value = mock.sentinel.pipe_name
        if serial_console_enabled:
            self.flags(enabled=True, group='serial_console')
            self.flags(proxyclient_address=mock.sentinel.host,
                       group='serial_console')
            mock_acquire_port.return_value = mock.sentinel.port

        self._consolehandler._setup_handlers()

        pipe_handler = mock_pipe_handler_class(
            mock.sentinel.pipe_name,
            self._consolehandler._input_queue,
            self._consolehandler._output_queue,
            self._consolehandler._client_connected,
            mock.sentinel.log_path)
        self.assertEqual(pipe_handler,
                         self._consolehandler._named_pipe_handler)

        serial_proxy = None
        if serial_console_enabled:
            serial_proxy = mock_serial_proxy_class(
                self._FAKE_INSTANCE_NAME,
                mock.sentinel.host, mock.sentinel.port,
                self._consolehandler._input_queue,
                self._consolehandler._output_queue,
                self._consolehandler._client_connected)
            self.assertEqual(mock.sentinel.host,
                             self._consolehandler._listen_host)
            self.assertEqual(mock.sentinel.port,
                             self._consolehandler._listen_port)
        self.assertEqual(serial_proxy,
                         self._consolehandler._serial_proxy)

    def test_setup_handlers(self):
        self._test_setup_handlers()

    def test_setup_handlers_console_disabled(self):
        self._test_setup_handlers(serial_console_enabled=False)

    @mock.patch.object(vmutils.VMUtils, 'get_vm_serial_port_connection')
    def test_setup_handlers_serial_unavailable(self, mock_get_serial_port):
        mock_get_serial_port.return_value = None
        self.assertRaises(vmutils.HyperVException,
                          self._consolehandler._setup_handlers)

    @mock.patch('nova.console.type.ConsoleSerial')
    def _test_get_serial_console(self, mock_serial_console,
                                 console_enabled=True):
        self.flags(enabled=console_enabled, group='serial_console')

        if console_enabled:
            self._consolehandler._listen_host = mock.sentinel.host
            self._consolehandler._listen_port = mock.sentinel.port

            expected = mock_serial_console(host=mock.sentinel.host,
                                           port=mock.sentinel.port)
            ret_val = self._consolehandler.get_serial_console()
            self.assertEqual(expected, ret_val)
        else:
            self.assertRaises(exception.ConsoleTypeUnavailable,
                              self._consolehandler.get_serial_console)

    def test_get_serial_console(self):
        self._test_get_serial_console()

    def test_get_serial_console_disabled(self):
        self._test_get_serial_console(console_enabled=False)
