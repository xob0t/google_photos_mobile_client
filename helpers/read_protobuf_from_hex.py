import blackboxprotobuf

protobuf_hex = "0a076578616d706c651001"

protobuf_bytes = bytes.fromhex(protobuf_hex)
decoded_data, message_type = blackboxprotobuf.decode_message(protobuf_bytes)

print("Decoded Data:", decoded_data)
print("Message Type:", message_type)

reencoded_bytes = blackboxprotobuf.encode_message(decoded_data, message_type)
print("Re-encoded Bytes:", reencoded_bytes.hex())
