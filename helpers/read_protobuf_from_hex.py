import blackboxprotobuf

protobuf_hex = "0a076578616d706c651001"

protobuf_bytes = bytes.fromhex(protobuf_hex)
decoded_data, message_type = blackboxprotobuf.decode_message(protobuf_bytes)

print("Decoded Data:\n", decoded_data)
print("Message Type:\n", message_type)

if protobuf_hex == blackboxprotobuf.encode_message(decoded_data, message_type).hex():
    print("Re-encode success")
else:
    print("Re-encode fail")
