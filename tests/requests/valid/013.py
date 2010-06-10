request = {
    "method": "POST",
    "uri": uri("/chunked_w_extensions"),
    "version": (1, 1),
    "headers": [
        ("Transfer-Encoding", "chunked")
    ],
    "body": "hello world"
}