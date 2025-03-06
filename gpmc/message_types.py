"""Protobuf message types"""

COMMIT_UPLOAD = {
    "1": {
        "type": "message",
        "message_typedef": {
            "1": {"type": "message", "message_typedef": {"1": {"type": "int"}, "2": {"type": "bytes"}}},
            "2": {"type": "string"},
            "3": {"type": "bytes"},
            "4": {"type": "message", "message_typedef": {"1": {"type": "int"}, "2": {"type": "int"}}},
            "7": {"type": "int"},
            "8": {
                "type": "message",
                "message_typedef": {
                    "1": {
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "string"},
                            "3": {"type": "string"},
                            "4": {"type": "string"},
                            "5": {"type": "message", "message_typedef": {"1": {"type": "string"}, "2": {"type": "string"}, "3": {"type": "string"}, "4": {"type": "string"}, "5": {"type": "string"}, "7": {"type": "string"}}},
                            "6": {"type": "string"},
                            "7": {"type": "message", "message_typedef": {"2": {"type": "string"}}},
                            "15": {"type": "string"},
                            "16": {"type": "string"},
                            "17": {"type": "string"},
                            "19": {"type": "string"},
                            "20": {"type": "string"},
                            "21": {"type": "message", "message_typedef": {"5": {"type": "message", "message_typedef": {"3": {"type": "string"}}}, "6": {"type": "string"}}},
                            "25": {"type": "string"},
                            "30": {"type": "message", "message_typedef": {"2": {"type": "string"}}},
                            "31": {"type": "string"},
                            "32": {"type": "string"},
                            "33": {"type": "message", "message_typedef": {"1": {"type": "string"}}},
                            "34": {"type": "string"},
                            "36": {"type": "string"},
                            "37": {"type": "string"},
                            "38": {"type": "string"},
                            "39": {"type": "string"},
                            "40": {"type": "string"},
                            "41": {"type": "string"},
                        },
                    },
                    "5": {
                        "type": "message",
                        "message_typedef": {
                            "2": {
                                "type": "message",
                                "message_typedef": {
                                    "2": {"type": "message", "message_typedef": {"3": {"type": "message", "message_typedef": {"2": {"type": "string"}}}, "4": {"type": "message", "message_typedef": {"2": {"type": "string"}}}}},
                                    "4": {"type": "message", "message_typedef": {"2": {"type": "message", "message_typedef": {"2": {"type": "int"}}}}},
                                    "5": {"type": "message", "message_typedef": {"2": {"type": "string"}}},
                                    "6": {"type": "int"},
                                },
                            },
                            "3": {
                                "type": "message",
                                "message_typedef": {
                                    "2": {"type": "message", "message_typedef": {"3": {"type": "string"}, "4": {"type": "string"}}},
                                    "3": {"type": "message", "message_typedef": {"2": {"type": "string"}, "3": {"type": "message", "message_typedef": {"2": {"type": "int"}}}}},
                                    "4": {"type": "string"},
                                    "5": {"type": "message", "message_typedef": {"2": {"type": "message", "message_typedef": {"2": {"type": "int"}}}}},
                                    "7": {"type": "string"},
                                },
                            },
                            "4": {"type": "message", "message_typedef": {"2": {"type": "message", "message_typedef": {"2": {"type": "string"}}}}},
                            "5": {
                                "type": "message",
                                "message_typedef": {
                                    "1": {
                                        "type": "message",
                                        "message_typedef": {
                                            "2": {"type": "message", "message_typedef": {"3": {"type": "string"}, "4": {"type": "string"}}},
                                            "3": {"type": "message", "message_typedef": {"2": {"type": "string"}, "3": {"type": "message", "message_typedef": {"2": {"type": "int"}}}}},
                                        },
                                    },
                                    "3": {"type": "int"},
                                },
                            },
                        },
                    },
                    "8": {"type": "string"},
                    "9": {
                        "type": "message",
                        "message_typedef": {
                            "2": {"type": "string"},
                            "3": {"type": "message", "message_typedef": {"1": {"type": "string"}, "2": {"type": "string"}}},
                            "4": {
                                "type": "message",
                                "message_typedef": {
                                    "1": {
                                        "type": "message",
                                        "message_typedef": {
                                            "3": {
                                                "type": "message",
                                                "message_typedef": {
                                                    "1": {
                                                        "type": "message",
                                                        "message_typedef": {
                                                            "1": {"type": "message", "message_typedef": {"5": {"type": "message", "message_typedef": {"1": {"type": "string"}}}, "6": {"type": "string"}}},
                                                            "2": {"type": "string"},
                                                            "3": {
                                                                "type": "message",
                                                                "message_typedef": {
                                                                    "1": {"type": "message", "message_typedef": {"5": {"type": "message", "message_typedef": {"1": {"type": "string"}}}, "6": {"type": "string"}}},
                                                                    "2": {"type": "string"},
                                                                },
                                                            },
                                                        },
                                                    }
                                                },
                                            },
                                            "4": {"type": "message", "message_typedef": {"1": {"type": "message", "message_typedef": {"2": {"type": "string"}}}}},
                                        },
                                    }
                                },
                            },
                        },
                    },
                    "11": {
                        "type": "message",
                        "message_typedef": {"2": {"type": "string"}, "3": {"type": "string"}, "4": {"type": "message", "message_typedef": {"2": {"type": "message", "message_typedef": {"1": {"type": "int"}, "2": {"type": "int"}}}}}},
                    },
                    "12": {"type": "string"},
                    "14": {
                        "type": "message",
                        "message_typedef": {"2": {"type": "string"}, "3": {"type": "string"}, "4": {"type": "message", "message_typedef": {"2": {"type": "message", "message_typedef": {"1": {"type": "int"}, "2": {"type": "int"}}}}}},
                    },
                    "15": {"type": "message", "message_typedef": {"1": {"type": "string"}, "4": {"type": "string"}}},
                    "17": {"type": "message", "message_typedef": {"1": {"type": "string"}, "4": {"type": "string"}}},
                    "19": {
                        "type": "message",
                        "message_typedef": {"2": {"type": "string"}, "3": {"type": "string"}, "4": {"type": "message", "message_typedef": {"2": {"type": "message", "message_typedef": {"1": {"type": "int"}, "2": {"type": "int"}}}}}},
                    },
                    "22": {"type": "string"},
                    "23": {"type": "string"},
                },
            },
            "10": {"type": "int"},
            "17": {"type": "int"},
        },
    },
    "2": {"type": "message", "message_typedef": {"3": {"type": "string"}, "4": {"type": "string"}, "5": {"type": "int"}}},
    "3": {"type": "bytes"},
}

CREATE_ALBUM = {
    "1": {"type": "string"},
    "2": {"type": "int"},
    "3": {"type": "int"},
    "4": {"seen_repeated": True, "field_order": ["1"], "message_typedef": {"1": {"field_order": ["1"], "message_typedef": {"1": {"type": "string"}}, "type": "message"}}, "type": "message"},
    "6": {"message_typedef": {}, "type": "message"},
    "7": {"field_order": ["1"], "message_typedef": {"1": {"type": "int"}}, "type": "message"},
    "8": {"field_order": ["3", "4", "5"], "message_typedef": {"3": {"type": "string"}, "4": {"type": "string"}, "5": {"type": "int"}}, "type": "message"},
}

MOVE_TO_TRASH = {
    "2": {"type": "int"},
    "3": {"type": "string"},
    "4": {"type": "int"},
    "8": {
        "field_order": ["4"],
        "message_typedef": {
            "4": {
                "field_order": ["2", "3", "4", "5"],
                "message_typedef": {
                    "2": {"message_typedef": {}, "type": "message"},
                    "3": {
                        "field_order": ["1"],
                        "message_typedef": {
                            "1": {"message_typedef": {}, "type": "message"},
                        },
                        "type": "message",
                    },
                    "4": {"message_typedef": {}, "type": "message"},
                    "5": {
                        "field_order": ["1"],
                        "message_typedef": {
                            "1": {"message_typedef": {}, "type": "message"},
                        },
                        "type": "message",
                    },
                },
                "type": "message",
            }
        },
        "type": "message",
    },
    "9": {"field_order": ["1", "2"], "message_typedef": {"1": {"type": "int"}, "2": {"field_order": ["1", "2"], "message_typedef": {"1": {"type": "int"}, "2": {"type": "string"}}, "type": "message"}}, "type": "message"},
}

FIND_REMOTE_MEDIA_BY_HASH = {
    "1": {
        "field_order": ["1", "2"],
        "message_typedef": {
            "1": {
                "field_order": ["1"],
                "message_typedef": {
                    "1": {"type": "bytes"},
                },
                "type": "message",
            },
            "2": {"message_typedef": {}, "type": "message"},
        },
        "type": "message",
    },
}

GET_UPLOAD_TOKEN = {
    "1": {"type": "int"},
    "2": {"type": "int"},
    "3": {"type": "int"},
    "4": {"type": "int"},
    "7": {"type": "int"},
}

ADD_MEDIA_TO_ALBUM = {
    "1": {"type": "string"},
    "2": {"type": "string"},
    "5": {"field_order": ["1"], "message_typedef": {"1": {"type": "int"}}, "type": "message"},
    "6": {
        "field_order": ["3", "4", "5"],
        "message_typedef": {
            "3": {"type": "string"},
            "4": {"type": "string"},
            "5": {"type": "int"},
        },
        "type": "message",
    },
    "7": {"type": "int"},
}
