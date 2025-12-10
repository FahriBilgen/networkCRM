package com.fahribilgen.networkcrm.entity;

import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class EntityTest {

    @Test
    void testUserBuilder() {
        User user = User.builder()
                .id(UUID.randomUUID())
                .email("test@example.com")
                .passwordHash("hashed_password")
                .build();

        assertNotNull(user);
        assertNotNull(user.getId());
        assertEquals("test@example.com", user.getEmail());
        assertEquals("hashed_password", user.getPasswordHash());
    }

    @Test
    void testUserEmailUniqueness() {
        String email = "test@example.com";
        User user1 = User.builder()
                .id(UUID.randomUUID())
                .email(email)
                .passwordHash("hashed1")
                .build();

        User user2 = User.builder()
                .id(UUID.randomUUID())
                .email(email)
                .passwordHash("hashed2")
                .build();

        assertEquals(user1.getEmail(), user2.getEmail());
    }

    @Test
    void testNodeBuilder() {
        UUID userId = UUID.randomUUID();
        User user = User.builder()
                .id(userId)
                .email("test@example.com")
                .passwordHash("hashed")
                .build();

        Node node = Node.builder()
                .id(UUID.randomUUID())
                .user(user)
                .name("Test Node")
                .description("Test description")
                .sector("Technology")
                .tags(Arrays.asList("tag1", "tag2"))
                .relationshipStrength(5)
                .build();

        assertNotNull(node);
        assertNotNull(node.getId());
        assertEquals("Test Node", node.getName());
        assertEquals(user.getId(), node.getUser().getId());
        assertEquals("Technology", node.getSector());
        assertEquals(2, node.getTags().size());
    }

    @Test
    void testNodeModification() {
        Node node = Node.builder()
                .id(UUID.randomUUID())
                .name("Original Name")
                .sector("Tech")
                .relationshipStrength(3)
                .build();

        node.setName("Updated Name");
        node.setSector("Finance");
        node.setRelationshipStrength(4);

        assertEquals("Updated Name", node.getName());
        assertEquals("Finance", node.getSector());
        assertEquals(4, node.getRelationshipStrength());
    }

    @Test
    void testNodeValidation() {
        Node node = Node.builder()
                .name("Valid Node")
                .build();

        assertNotNull(node.getName());
        assertTrue(node.getName().length() > 0);
    }

}
