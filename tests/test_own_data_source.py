from your_app.common import remote_data

def test_new_app_reads_only_its_own_release_by_default():
    for value in (remote_data.DEFAULT_RELEASE_API,remote_data.DEFAULT_MANIFEST_URL,remote_data.DEFAULT_FALLBACK_MANIFEST_URL,remote_data.DEFAULT_ASSET_BASE_URL):
        assert '/oqq21/mapleland-item-search/' in value
        assert '/oqq21/ppoo213/' not in value
