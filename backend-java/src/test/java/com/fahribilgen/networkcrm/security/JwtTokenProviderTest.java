package com.fahribilgen.networkcrm.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.Authentication;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class JwtTokenProviderTest {

    private JwtTokenProvider tokenProvider;
    private static final String TEST_SECRET = "your_secret_key_with_minimum_256_bits_length_for_HS256_algorithm";
    private static final int TEST_EXPIRATION = 86400000;

    @BeforeEach
    void setUp() {
        tokenProvider = new JwtTokenProvider();
        ReflectionTestUtils.setField(tokenProvider, "jwtSecret", TEST_SECRET);
        ReflectionTestUtils.setField(tokenProvider, "jwtExpirationInMs", TEST_EXPIRATION);
    }

    @Test
    void testGenerateToken() {
        Authentication authentication = mock(Authentication.class);
        UserPrincipal userPrincipal = UserPrincipal.builder()
                .id(UUID.fromString("123e4567-e89b-12d3-a456-426614174000"))
                .email("test@example.com")
                .build();

        when(authentication.getPrincipal()).thenReturn(userPrincipal);

        String token = tokenProvider.generateToken(authentication);

        assertNotNull(token);
        assertFalse(token.isEmpty());
    }

    @Test
    void testGetUserIdFromToken() {
        Authentication authentication = mock(Authentication.class);
        UserPrincipal userPrincipal = UserPrincipal.builder()
                .id(UUID.fromString("123e4567-e89b-12d3-a456-426614174000"))
                .email("test@example.com")
                .build();

        when(authentication.getPrincipal()).thenReturn(userPrincipal);

        String token = tokenProvider.generateToken(authentication);
        UUID userId = tokenProvider.getUserIdFromJWT(token);

        assertNotNull(userId);
        assertEquals(UUID.fromString("123e4567-e89b-12d3-a456-426614174000"), userId);
    }

    @Test
    void testValidateToken_Valid() {
        Authentication authentication = mock(Authentication.class);
        UserPrincipal userPrincipal = UserPrincipal.builder()
                .id(UUID.fromString("123e4567-e89b-12d3-a456-426614174000"))
                .email("test@example.com")
                .build();

        when(authentication.getPrincipal()).thenReturn(userPrincipal);

        String token = tokenProvider.generateToken(authentication);
        boolean isValid = tokenProvider.validateToken(token);

        assertTrue(isValid);
    }

    @Test
    void testValidateToken_Invalid() {
        String invalidToken = "invalid.token.here";
        boolean isValid = tokenProvider.validateToken(invalidToken);

        assertFalse(isValid);
    }

    @Test
    void testValidateToken_Expired() {
        // Set very short expiration
        ReflectionTestUtils.setField(tokenProvider, "jwtExpirationInMs", 1);

        Authentication authentication = mock(Authentication.class);
        UserPrincipal userPrincipal = UserPrincipal.builder()
                .id(UUID.fromString("123e4567-e89b-12d3-a456-426614174000"))
                .email("test@example.com")
                .build();

        when(authentication.getPrincipal()).thenReturn(userPrincipal);

        String token = tokenProvider.generateToken(authentication);

        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        boolean isValid = tokenProvider.validateToken(token);
        assertFalse(isValid);
    }

}
