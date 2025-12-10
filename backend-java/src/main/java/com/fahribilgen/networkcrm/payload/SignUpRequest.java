package com.fahribilgen.networkcrm.payload;

import lombok.Data;

@Data
public class SignUpRequest {
    private String email;
    private String password;
}
