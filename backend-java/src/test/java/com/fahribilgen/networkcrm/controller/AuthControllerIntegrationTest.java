package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.JwtAuthenticationResponse;
import com.fahribilgen.networkcrm.payload.LoginRequest;
import com.fahribilgen.networkcrm.payload.SignUpRequest;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.JwtTokenProvider;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Optional;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class AuthControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private UserRepository userRepository;

    @MockBean
    private JwtTokenProvider tokenProvider;

    @Autowired
    private PasswordEncoder passwordEncoder;

    private User testUser;
    private LoginRequest loginRequest;
    private SignUpRequest signUpRequest;

    @BeforeEach
    void setUp() {
        testUser = User.builder()
                .id(UUID.randomUUID())
                .email("test@example.com")
                .passwordHash(passwordEncoder.encode("password123"))
                .build();

        loginRequest = LoginRequest.builder()
                .email("test@example.com")
                .password("password123")
                .build();

        signUpRequest = SignUpRequest.builder()
                .email("newuser@example.com")
                .password("password123")
                .build();
    }

    @Test
    void testSignIn_Success() throws Exception {
        when(userRepository.findByEmail("test@example.com"))
                .thenReturn(Optional.of(testUser));
        when(tokenProvider.generateToken(any()))
                .thenReturn("jwt_token_here");

        mockMvc.perform(post("/api/auth/signin")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(loginRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").value("jwt_token_here"));
    }

    @Test
    void testSignIn_InvalidCredentials() throws Exception {
        when(userRepository.findByEmail("test@example.com"))
                .thenReturn(Optional.empty());

        mockMvc.perform(post("/api/auth/signin")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(loginRequest)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void testSignUp_Success() throws Exception {
        User newUser = User.builder()
                .id(UUID.randomUUID())
                .email("newuser@example.com")
                .passwordHash(passwordEncoder.encode("password123"))
                .build();

        when(userRepository.existsByEmail("newuser@example.com"))
                .thenReturn(false);
        when(userRepository.save(any(User.class)))
                .thenReturn(newUser);
        when(tokenProvider.generateToken(any()))
                .thenReturn("jwt_token_here");

        mockMvc.perform(post("/api/auth/signup")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(signUpRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").value("jwt_token_here"));
    }

    @Test
    void testSignUp_EmailAlreadyExists() throws Exception {
        when(userRepository.existsByEmail("newuser@example.com"))
                .thenReturn(true);

        mockMvc.perform(post("/api/auth/signup")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(signUpRequest)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void testSignUp_InvalidEmail() throws Exception {
        SignUpRequest invalidRequest = SignUpRequest.builder()
                .email("invalid-email")
                .password("password123")
                .build();

        mockMvc.perform(post("/api/auth/signup")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(invalidRequest)))
                .andExpect(status().isBadRequest());
    }

}
