request = {
    "method": "POST",
    "uri": uri("/chunked_w_trailing_headers"),
    "version": (1, 1),
    "headers": [
        ("Transfer-Encoding", "chunked")
    ],
    "body": "hello world",
    "trailers": [
        ("Vary", "*"),
        ("Content-Type", "text/plain")
    ]
}