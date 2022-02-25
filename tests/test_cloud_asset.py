from unittest import TestCase

import pytest
from parameterized import parameterized

from censys.cloud_connectors.common.cloud_asset import (
    CloudAsset,
    GcpCloudStorageAsset,
    ObjectStorageAsset,
)

TEST_TYPE = "test_type"
TEST_VALUE = "test_value"
TEST_CSP_LABEL = "test_csp_label"
TEST_SCAN_DATA = {"test_scan_data": "test_scan_data"}
TEST_UID = "test_uid"


class CloudAssetTest(TestCase):
    def test_cloud_asset_to_dict(self):
        cloud_asset = CloudAsset(
            type=TEST_TYPE,
            value=TEST_VALUE,
            cspLabel=TEST_CSP_LABEL,
            scan_data=TEST_SCAN_DATA,
            uid=TEST_UID,
        )
        assert cloud_asset.uid == TEST_UID
        assert cloud_asset.to_dict() == {
            "type": TEST_TYPE,
            "value": TEST_VALUE,
            "cspLabel": TEST_CSP_LABEL,
            "scanData": '{"test_scan_data": "test_scan_data"}',
        }

    def test_object_storage_asset(self):
        cloud_asset = ObjectStorageAsset(
            value=TEST_VALUE, cspLabel=TEST_CSP_LABEL, uid=TEST_UID
        )
        assert cloud_asset.type == "OBJECT_STORAGE"

    def test_gcp_cloud_storage_asset(self):
        test_object_name = "test-bucket"
        test_value = f"https://storage.googleapis.com/{test_object_name}"
        cloud_asset = GcpCloudStorageAsset(value=test_value, uid=test_object_name)
        assert cloud_asset.type == "OBJECT_STORAGE"
        assert cloud_asset.value == test_value
        assert cloud_asset.cspLabel == "GCP"
        assert cloud_asset.scan_data == {}
        assert cloud_asset.uid == "test-bucket"

    @parameterized.expand(
        [
            (
                "http://not.valid.bucket/url",
                "Bucket name must start with https://storage.googleapis.com/",
            ),
        ]
    )
    def test_gcp_cloud_storage_asset_validation(self, value, expected_error):
        with pytest.raises(ValueError, match=expected_error):
            GcpCloudStorageAsset(value=value, uid=TEST_UID)