package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.impl.NodeServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class NodeServiceTest {

    @Mock
    private NodeRepository nodeRepository;

    @Mock
    private EmbeddingService embeddingService;

    @InjectMocks
    private NodeServiceImpl nodeService;

    private User testUser;
    private Node testNode;
    private NodeRequest nodeRequest;

    @BeforeEach
    void setUp() {
        testUser = User.builder()
                .id(UUID.randomUUID())
                .email("test@example.com")
                .passwordHash("hashed_password")
                .build();

        testNode = Node.builder()
                .id(UUID.randomUUID())
                .user(testUser)
                .type(NodeType.PERSON)
                .name("John Doe")
                .description("Test person")
                .sector("Technology")
                .tags(Arrays.asList("tech", "ai"))
                .relationshipStrength(5)
                .build();

        nodeRequest = NodeRequest.builder()
                .type(NodeType.PERSON)
                .name("John Doe")
                .description("Test person")
                .sector("Technology")
                .tags(Arrays.asList("tech", "ai"))
                .relationshipStrength(5)
                .build();

        // Setup embedding service mock
        when(embeddingService.generateEmbedding(anyString()))
                .thenReturn(Arrays.asList(0.1, 0.2, 0.3));
    }

    @Test
    void testCreateNode_Success() {
        when(nodeRepository.save(any(Node.class))).thenReturn(testNode);

        NodeResponse response = nodeService.createNode(nodeRequest, testUser);

        assertNotNull(response);
        assertEquals("John Doe", response.getName());
        assertEquals(NodeType.PERSON, response.getType());
        assertEquals("Technology", response.getSector());
        verify(nodeRepository, times(1)).save(any(Node.class));
    }

    @Test
    void testCreateNode_InvalidInput() {
        NodeRequest invalidRequest = NodeRequest.builder()
                .type(NodeType.PERSON)
                .name(null)
                .build();

        assertThrows(IllegalArgumentException.class, () -> 
            nodeService.createNode(invalidRequest, testUser)
        );
    }

    @Test
    void testGetNode_Success() {
        UUID nodeId = testNode.getId();
        when(nodeRepository.findById(nodeId)).thenReturn(Optional.of(testNode));

        NodeResponse response = nodeService.getNode(nodeId, testUser);

        assertNotNull(response);
        assertEquals(testNode.getName(), response.getName());
        verify(nodeRepository, times(1)).findById(nodeId);
    }

    @Test
    void testGetNode_NotFound() {
        UUID nonExistentId = UUID.randomUUID();
        when(nodeRepository.findById(nonExistentId)).thenReturn(Optional.empty());

        assertThrows(RuntimeException.class, () -> 
            nodeService.getNode(nonExistentId, testUser)
        );
    }

    @Test
    void testUpdateNode_Success() {
        UUID nodeId = testNode.getId();
        NodeRequest updateRequest = NodeRequest.builder()
                .type(NodeType.PERSON)
                .name("Jane Doe")
                .description("Updated description")
                .sector("Finance")
                .relationshipStrength(4)
                .build();

        testNode.setName("Jane Doe");
        testNode.setDescription("Updated description");
        testNode.setSector("Finance");
        testNode.setRelationshipStrength(4);

        when(nodeRepository.findById(nodeId)).thenReturn(Optional.of(testNode));
        when(nodeRepository.save(any(Node.class))).thenReturn(testNode);

        NodeResponse response = nodeService.updateNode(nodeId, updateRequest, testUser);

        assertNotNull(response);
        assertEquals("Jane Doe", response.getName());
        assertEquals("Finance", response.getSector());
        verify(nodeRepository, times(1)).findById(nodeId);
        verify(nodeRepository, times(1)).save(any(Node.class));
    }

    @Test
    void testDeleteNode_Success() {
        UUID nodeId = testNode.getId();
        when(nodeRepository.findById(nodeId)).thenReturn(Optional.of(testNode));

        nodeService.deleteNode(nodeId, testUser);

        verify(nodeRepository, times(1)).deleteById(nodeId);
    }

    @Test
    void testGetAllNodes() {
        List<Node> nodes = Arrays.asList(testNode);
        when(nodeRepository.findByUserId(testUser.getId())).thenReturn(nodes);

        List<NodeResponse> responses = nodeService.getAllNodes(testUser);

        assertNotNull(responses);
        assertEquals(1, responses.size());
        verify(nodeRepository, times(1)).findByUserId(testUser.getId());
    }

    @Test
    void testGetNodesByType() {
        List<Node> nodes = Arrays.asList(testNode);
        when(nodeRepository.findByUserIdAndType(testUser.getId(), NodeType.PERSON))
                .thenReturn(nodes);

        List<NodeResponse> responses = nodeService.getNodesByType(NodeType.PERSON, testUser);

        assertNotNull(responses);
        assertEquals(1, responses.size());
        assertTrue(responses.get(0).getType() == NodeType.PERSON);
    }

    @Test
    void testFindSimilarNodes() {
        List<Node> nodes = Arrays.asList(testNode);
        when(nodeRepository.findByUserId(testUser.getId())).thenReturn(nodes);

        List<NodeResponse> results = nodeService.findSimilarNodes("John", testUser);

        assertNotNull(results);
        verify(nodeRepository, times(1)).findByUserId(testUser.getId());
    }

}

