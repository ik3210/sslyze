# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest

import logging

import pickle

from nassl.ssl_client import ClientCertificateRequested

from sslyze.plugins.fallback_scsv_plugin import FallbackScsvPlugin, FallbackScsvScanCommand
from sslyze.server_connectivity_tester import ServerConnectivityTester
from sslyze.ssl_settings import ClientAuthenticationServerConfigurationEnum, ClientAuthenticationCredentials
from tests.openssl_server import NotOnLinux64Error
from tests.openssl_server import VulnerableOpenSslServer


class FallbackScsvPluginTestCase(unittest.TestCase):

    def test_fallback_good(self):
        server_test = ServerConnectivityTester(hostname='www.google.com')
        server_info = server_test.perform()

        plugin = FallbackScsvPlugin()
        plugin_result = plugin.process_task(server_info, FallbackScsvScanCommand())

        self.assertTrue(plugin_result.supports_fallback_scsv)

        self.assertTrue(plugin_result.as_text())
        self.assertTrue(plugin_result.as_xml())

        # Ensure the results are pickable so the ConcurrentScanner can receive them via a Queue
        self.assertTrue(pickle.dumps(plugin_result))

    def test_fallback_bad(self):
        try:
            with VulnerableOpenSslServer() as server:
                server_test = ServerConnectivityTester(hostname=server.hostname, ip_address=server.ip_address,
                                                         port=server.port)
                server_info = server_test.perform()

                plugin = FallbackScsvPlugin()
                plugin_result = plugin.process_task(server_info, FallbackScsvScanCommand())
        except NotOnLinux64Error:
            # The test suite only has the vulnerable OpenSSL version compiled for Linux 64 bits
            logging.warning('WARNING: Not on Linux - skipping test_fallback_bad() test')
            return

        self.assertFalse(plugin_result.supports_fallback_scsv)
        self.assertTrue(plugin_result.as_text())
        self.assertTrue(plugin_result.as_xml())

        # Ensure the results are pickable so the ConcurrentScanner can receive them via a Queue
        self.assertTrue(pickle.dumps(plugin_result))

    def test_fails_when_client_auth_failed(self):
        # Given a server that requires client authentication
        try:
            with VulnerableOpenSslServer(
                    client_auth_config=ClientAuthenticationServerConfigurationEnum.REQUIRED
            ) as server:
                # And the client does NOT provide a client certificate
                server_test = ServerConnectivityTester(
                    hostname=server.hostname,
                    ip_address=server.ip_address,
                    port=server.port
                )
                server_info = server_test.perform()

                # The plugin fails when a client cert was not supplied
                plugin = FallbackScsvPlugin()
                with self.assertRaises(ClientCertificateRequested):
                    plugin.process_task(server_info, FallbackScsvScanCommand())

        except NotOnLinux64Error:
            logging.warning('WARNING: Not on Linux - skipping test')
            return

    def test_works_when_client_auth_succeeded(self):
        # Given a server that requires client authentication
        try:
            with VulnerableOpenSslServer(
                    client_auth_config=ClientAuthenticationServerConfigurationEnum.REQUIRED
            ) as server:
                # And the client provides a client certificate
                client_creds = ClientAuthenticationCredentials(
                    client_certificate_chain_path=server.get_client_certificate_path(),
                    client_key_path=server.get_client_key_path(),
                )

                server_test = ServerConnectivityTester(
                    hostname=server.hostname,
                    ip_address=server.ip_address,
                    port=server.port,
                    client_auth_credentials=client_creds,
                )
                server_info = server_test.perform()

                # The plugin works fine
                plugin = FallbackScsvPlugin()
                plugin_result = plugin.process_task(server_info, FallbackScsvScanCommand())

        except NotOnLinux64Error:
            logging.warning('WARNING: Not on Linux - skipping test')
            return

        self.assertFalse(plugin_result.supports_fallback_scsv)

        self.assertTrue(plugin_result.as_text())
        self.assertTrue(plugin_result.as_xml())