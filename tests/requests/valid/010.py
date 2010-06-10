request = {
    "method": "POST",
    "uri": uri("/post_chunked_all_your_base"),
    "version": (1, 1),
    "headers": [
        ("Transfer-Encoding", "chunked"),
    ],
    "body": "all your base are belong to us"
}