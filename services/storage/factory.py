from services.storage.backend import LocalStorageBackend, StorageBackend


def get_storage_backend(
    storage_backend: str,
    supabase_url: str,
    supabase_service_role_key: str,
    supabase_storage_bucket: str,
) -> StorageBackend:
    if storage_backend == "supabase":
        from services.storage.supabase_backend import SupabaseStorageBackend

        return SupabaseStorageBackend(
            project_url=supabase_url,
            service_role_key=supabase_service_role_key,
            bucket=supabase_storage_bucket,
        )
    return LocalStorageBackend()
