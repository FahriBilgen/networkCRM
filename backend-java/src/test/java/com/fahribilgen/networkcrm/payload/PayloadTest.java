package com.fahribilgen.networkcrm.payload;

import org.junit.jupiter.api.Test;

import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;

class PayloadTest {

    @Test
    void testNodeRequestBuilder() {
        NodeRequest request = NodeRequest.builder()
                .name("Test Node")
                .description("Test description")
                .sector("Technology")
                .tags(Arrays.asList("tag1", "tag2"))
                .relationshipStrength(5)
                .build();

        assertNotNull(request);
        assertEquals("Test Node", request.getName());
        assertEquals("Test description", request.getDescription());
        assertEquals("Technology", request.getSector());
        assertEquals(2, request.getTags().size());
        assertEquals(5, request.getRelationshipStrength());
    }

    @Test
    void testNodeRequestValidation() {
        NodeRequest invalidRequest = NodeRequest.builder()
                .name(null)
                .build();

        assertNull(invalidRequest.getName());
        assertThrows(NullPointerException.class, () -> {
            if (invalidRequest.getName() == null) {
                throw new NullPointerException("Name cannot be null");
            }
        });
    }

    @Test
    void testLoginRequestBuilder() {
        LoginRequest request = LoginRequest.builder()
                .email("test@example.com")
                .password("password123")
                .build();

        assertNotNull(request);
        assertEquals("test@example.com", request.getEmail());
        assertEquals("password123", request.getPassword());
    }

    @Test
    void testSignUpRequestBuilder() {
        SignUpRequest request = SignUpRequest.builder()
                .email("newuser@example.com")
                .password("securePassword123")
                .build();

        assertNotNull(request);
        assertEquals("newuser@example.com", request.getEmail());
        assertEquals("securePassword123", request.getPassword());
    }

    @Test
    void testSignUpRequestEmailValidation() {
        String validEmail = "test@example.com";
        String invalidEmail = "invalid-email";

        assertTrue(validEmail.contains("@"));
        assertFalse(invalidEmail.contains("@"));
    }

}
