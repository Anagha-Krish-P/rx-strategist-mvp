def next_upload_state(previous_file_id, new_file_id):
    return {
        "file_id": new_file_id,
        "invalidate_result": previous_file_id != new_file_id,
    }
