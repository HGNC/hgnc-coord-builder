"""Tests for the CLI controller pattern."""

from unittest.mock import MagicMock, patch

from hgnc_coord_builder.cli import main
from hgnc_coord_builder.exceptions import ConfigError, ServiceError

_WIRING_PATCHES = [
    "hgnc_coord_builder.repositories.wiring.build_genew4_engine",
    "hgnc_coord_builder.repositories.wiring.build_ncbi_repository",
    "hgnc_coord_builder.repositories.wiring.build_ensembl_repository",
    "hgnc_coord_builder.repositories.wiring.build_ccds_repository",
    "hgnc_coord_builder.repositories.wiring.build_cytoband_repository",
    "hgnc_coord_builder.repositories.wiring.build_pseudogene_repository",
    "hgnc_coord_builder.repositories.wiring.build_staging_repository",
]


class TestMainSuccess:
    def test_main_returns_zero_on_success(self) -> None:
        with patch("hgnc_coord_builder.cli.configure_logging"), \
             patch("hgnc_coord_builder.cli.Settings") as mock_settings_cls:
            for p in _WIRING_PATCHES:
                patch(p, return_value=MagicMock()).start()
            with patch("hgnc_coord_builder.cli.MainService") as mock_svc_cls:
                mock_settings_cls.return_value = MagicMock()
                mock_svc = MagicMock()
                mock_svc_cls.return_value = mock_svc
                result = main([])
        assert result == 0

    def test_main_calls_configure_logging(self) -> None:
        with patch("hgnc_coord_builder.cli.configure_logging") as mock_log, \
             patch("hgnc_coord_builder.cli.Settings") as mock_settings_cls:
            for p in _WIRING_PATCHES:
                patch(p, return_value=MagicMock()).start()
            with patch("hgnc_coord_builder.cli.MainService"):
                mock_settings_cls.return_value = MagicMock()
                main([])
        mock_log.assert_called_once()

    def test_main_loads_settings(self) -> None:
        with patch("hgnc_coord_builder.cli.configure_logging"), \
             patch("hgnc_coord_builder.cli.Settings") as mock_settings_cls:
            for p in _WIRING_PATCHES:
                patch(p, return_value=MagicMock()).start()
            with patch("hgnc_coord_builder.cli.MainService"):
                mock_settings_cls.return_value = MagicMock()
                main([])
        mock_settings_cls.assert_called_once()

    def test_main_calls_service_run(self) -> None:
        with patch("hgnc_coord_builder.cli.configure_logging"), \
             patch("hgnc_coord_builder.cli.Settings") as mock_settings_cls:
            for p in _WIRING_PATCHES:
                patch(p, return_value=MagicMock()).start()
            with patch("hgnc_coord_builder.cli.MainService") as mock_svc_cls:
                mock_settings_cls.return_value = MagicMock()
                mock_svc = MagicMock()
                mock_svc_cls.return_value = mock_svc
                main([])
        mock_svc.run.assert_called_once()


class TestMainConfigError:
    def test_config_error_returns_exit_code_2(self) -> None:
        with patch("hgnc_coord_builder.cli.configure_logging"), \
             patch("hgnc_coord_builder.cli.Settings", side_effect=ConfigError("bad config")):
            result = main([])
        assert result == 2

    def test_config_error_during_settings_load(self) -> None:
        with patch("hgnc_coord_builder.cli.configure_logging"), \
             patch("hgnc_coord_builder.cli.Settings", side_effect=ConfigError("missing env")):
            result = main([])
        assert result == 2


class TestMainServiceError:
    def test_service_error_returns_exit_code_3(self) -> None:
        with patch("hgnc_coord_builder.cli.configure_logging"), \
             patch("hgnc_coord_builder.cli.Settings") as mock_settings_cls:
            for p in _WIRING_PATCHES:
                patch(p, return_value=MagicMock()).start()
            with patch("hgnc_coord_builder.cli.MainService") as mock_svc_cls:
                mock_settings_cls.return_value = MagicMock()
                mock_svc = MagicMock()
                mock_svc.run.side_effect = ServiceError("domain failure")
                mock_svc_cls.return_value = mock_svc
                result = main([])
        assert result == 3


class TestMainUnexpectedError:
    def test_unexpected_error_returns_exit_code_1(self) -> None:
        with patch("hgnc_coord_builder.cli.configure_logging"), \
             patch("hgnc_coord_builder.cli.Settings") as mock_settings_cls:
            for p in _WIRING_PATCHES:
                patch(p, return_value=MagicMock()).start()
            with patch("hgnc_coord_builder.cli.MainService") as mock_svc_cls:
                mock_settings_cls.return_value = MagicMock()
                mock_svc = MagicMock()
                mock_svc.run.side_effect = RuntimeError("boom")
                mock_svc_cls.return_value = mock_svc
                result = main([])
        assert result == 1
