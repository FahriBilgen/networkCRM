package com.fahribilgen.networkcrm.repository;

import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.NodeType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase.Replace;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;

import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@DataJpaTest
@org.springframework.test.context.ActiveProfiles("test")
@org.springframework.test.context.TestPropertySource(locations = "classpath:application-test.properties")
class NodeRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private NodeRepository nodeRepository;

    private User testUser;
    private Node testNode1;
    private Node testNode2;

    @BeforeEach
    void setUp() {
        testUser = User.builder()
                .email("test@example.com")
                .passwordHash("hashed_password")
                .build();
        testUser = entityManager.persistAndFlush(testUser);

        testNode1 = Node.builder()
                .user(testUser)
                .type(NodeType.PERSON)
                .name("John Doe")
                .description("Test person 1")
                .sector("Technology")
                .relationshipStrength(5)
                .build();

        testNode2 = Node.builder()
                .user(testUser)
                .type(NodeType.VISION)
                .name("Global Tech Vision")
                .description("Test vision")
                .sector("Technology")
                .relationshipStrength(3)
                .build();

        testNode1 = entityManager.persistAndFlush(testNode1);
        testNode2 = entityManager.persistAndFlush(testNode2);
    }

    @Test
    void testFindByUserId() {
        List<Node> nodes = nodeRepository.findByUserId(testUser.getId());

        assertNotNull(nodes);
        assertEquals(2, nodes.size());
        assertTrue(nodes.stream().allMatch(n -> n.getUser().getId().equals(testUser.getId())));
    }

    @Test
    void testFindByUserId_EmptyResult() {
        UUID nonExistentUserId = UUID.randomUUID();
        List<Node> nodes = nodeRepository.findByUserId(nonExistentUserId);

        assertNotNull(nodes);
        assertEquals(0, nodes.size());
    }

    @Test
    void testFindByUserIdAndType() {
        List<Node> personNodes = nodeRepository.findByUserIdAndType(testUser.getId(), NodeType.PERSON);

        assertNotNull(personNodes);
        assertEquals(1, personNodes.size());
        assertEquals(NodeType.PERSON, personNodes.get(0).getType());
        assertEquals("John Doe", personNodes.get(0).getName());
    }

    @Test
    void testFindByUserIdAndType_DifferentType() {
        List<Node> visionNodes = nodeRepository.findByUserIdAndType(testUser.getId(), NodeType.VISION);

        assertNotNull(visionNodes);
        assertEquals(1, visionNodes.size());
        assertEquals(NodeType.VISION, visionNodes.get(0).getType());
    }

    @Test
    void testFindByUserIdAndType_NoResults() {
        List<Node> goalNodes = nodeRepository.findByUserIdAndType(testUser.getId(), NodeType.GOAL);

        assertNotNull(goalNodes);
        assertEquals(0, goalNodes.size());
    }

    @Test
    void testFindById() {
        Node node = nodeRepository.findById(testNode1.getId()).orElse(null);

        assertNotNull(node);
        assertEquals(testNode1.getId(), node.getId());
        assertEquals("John Doe", node.getName());
        assertEquals(NodeType.PERSON, node.getType());
    }

    @Test
    void testSaveNode() {
        Node newNode = Node.builder()
                .user(testUser)
                .type(NodeType.GOAL)
                .name("Career Goal")
                .description("Become a tech leader")
                .sector("Technology")
                .relationshipStrength(4)
                .build();

        Node savedNode = nodeRepository.save(newNode);
        entityManager.flush();

        assertNotNull(savedNode.getId());
        assertEquals("Career Goal", savedNode.getName());

        Node retrievedNode = nodeRepository.findById(savedNode.getId()).orElse(null);
        assertNotNull(retrievedNode);
        assertEquals("Career Goal", retrievedNode.getName());
    }

    @Test
    void testUpdateNode() {
        testNode1.setName("Updated Name");
        testNode1.setDescription("Updated description");
        Node updatedNode = nodeRepository.save(testNode1);
        entityManager.flush();

        Node retrievedNode = nodeRepository.findById(testNode1.getId()).orElse(null);
        assertNotNull(retrievedNode);
        assertEquals("Updated Name", retrievedNode.getName());
        assertEquals("Updated description", retrievedNode.getDescription());
    }

    @Test
    void testDeleteNode() {
        UUID nodeIdToDelete = testNode1.getId();
        nodeRepository.delete(testNode1);
        entityManager.flush();

        assertTrue(nodeRepository.findById(nodeIdToDelete).isEmpty());
    }

}
