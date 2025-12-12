package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.GoalPathSuggestionResponse;
import com.fahribilgen.networkcrm.payload.NodeFilterRequest;
import com.fahribilgen.networkcrm.payload.NodeProximityResponse;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.impl.NodeServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.jpa.domain.Specification;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class NodeServiceTest {

    @Mock
    private NodeRepository nodeRepository;

    @Mock
    private EdgeRepository edgeRepository;

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
    void testUpdateNode_PersistsTimelineProperties() {
        UUID nodeId = testNode.getId();
        Map<String, Object> properties = new HashMap<>();
        properties.put("timeline", List.of(
                Map.of("id", "entry-1", "date", "2025-01-01", "note", "First note")));

        NodeRequest updateRequest = NodeRequest.builder()
                .type(NodeType.PERSON)
                .name("Timeline Person")
                .properties(properties)
                .build();

        when(nodeRepository.findById(nodeId)).thenReturn(Optional.of(testNode));
        when(nodeRepository.save(any(Node.class))).thenAnswer(invocation -> invocation.getArgument(0));

        NodeResponse response = nodeService.updateNode(nodeId, updateRequest, testUser);

        assertNotNull(response.getProperties());
        assertEquals(properties.get("timeline"), response.getProperties().get("timeline"));
        verify(nodeRepository).save(any(Node.class));
    }

    @Test
    void testDeleteNode_Success() {
        UUID nodeId = testNode.getId();
        when(nodeRepository.findById(nodeId)).thenReturn(Optional.of(testNode));
        List<Edge> outgoing = Collections.singletonList(Edge.builder().id(UUID.randomUUID()).build());
        List<Edge> incoming = Collections.singletonList(Edge.builder().id(UUID.randomUUID()).build());
        when(edgeRepository.findBySourceNodeId(nodeId)).thenReturn(outgoing);
        when(edgeRepository.findByTargetNodeId(nodeId)).thenReturn(incoming);

        nodeService.deleteNode(nodeId, testUser);

        verify(edgeRepository, times(1)).deleteAll(outgoing);
        verify(edgeRepository, times(1)).deleteAll(incoming);
        verify(nodeRepository, times(1)).delete(testNode);
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
    void testFilterNodes_UsesSpecification() {
        NodeFilterRequest filterRequest = NodeFilterRequest.builder()
                .sector("Technology")
                .minRelationshipStrength(3)
                .build();

        when(nodeRepository.findAll(any(Specification.class))).thenReturn(List.of(testNode));

        List<NodeResponse> responses = nodeService.filterNodes(filterRequest, testUser);

        assertEquals(1, responses.size());
        verify(nodeRepository, times(1)).findAll(any(Specification.class));
    }

    @Test
    void testFindSimilarNodes() {
        List<Node> nodes = Arrays.asList(testNode);
        when(nodeRepository.findByUserId(testUser.getId())).thenReturn(nodes);

        List<NodeResponse> results = nodeService.findSimilarNodes("John", testUser);

        assertNotNull(results);
        verify(nodeRepository, times(1)).findByUserId(testUser.getId());
    }

    @Test
    void testGetNodeProximity() {
        UUID nodeId = testNode.getId();

        Node goalNode = Node.builder()
                .id(UUID.randomUUID())
                .user(testUser)
                .type(NodeType.GOAL)
                .name("MVP Launch")
                .build();

        Node personNode = Node.builder()
                .id(UUID.randomUUID())
                .user(testUser)
                .type(NodeType.PERSON)
                .name("Jane Mentor")
                .build();

        Edge outgoing = Edge.builder()
                .id(UUID.randomUUID())
                .sourceNode(testNode)
                .targetNode(goalNode)
                .type(EdgeType.SUPPORTS)
                .relationshipStrength(5)
                .build();

        Edge incoming = Edge.builder()
                .id(UUID.randomUUID())
                .sourceNode(personNode)
                .targetNode(testNode)
                .type(EdgeType.KNOWS)
                .relationshipStrength(3)
                .build();

        when(nodeRepository.findById(nodeId)).thenReturn(Optional.of(testNode));
        when(edgeRepository.findBySourceNodeId(nodeId)).thenReturn(List.of(outgoing));
        when(edgeRepository.findByTargetNodeId(nodeId)).thenReturn(List.of(incoming));

        NodeProximityResponse proximity = nodeService.getNodeProximity(nodeId, testUser);

        assertNotNull(proximity);
        assertEquals(2, proximity.getTotalConnections());
        assertEquals(2, proximity.getNeighbors().size());
        assertEquals(1L, proximity.getConnectionCounts().get(EdgeType.SUPPORTS));
        assertTrue(proximity.getInfluenceScore() > 0);
    }

    @Test
    void testGoalPathSuggestionsFindTwoHopPerson() {
        UUID goalId = UUID.randomUUID();
        Node goalNode = Node.builder()
                .id(goalId)
                .user(testUser)
                .type(NodeType.GOAL)
                .name("Fundraising")
                .build();

        Node intermediary = Node.builder()
                .id(UUID.randomUUID())
                .user(testUser)
                .type(NodeType.PERSON)
                .name("Ayse")
                .build();

        Node distantPerson = Node.builder()
                .id(UUID.randomUUID())
                .user(testUser)
                .type(NodeType.PERSON)
                .name("Bora")
                .build();

        List<Node> nodes = List.of(goalNode, intermediary, distantPerson);

        Edge firstEdge = Edge.builder()
                .id(UUID.randomUUID())
                .sourceNode(goalNode)
                .targetNode(intermediary)
                .type(EdgeType.SUPPORTS)
                .weight(3)
                .build();

        Edge secondEdge = Edge.builder()
                .id(UUID.randomUUID())
                .sourceNode(intermediary)
                .targetNode(distantPerson)
                .type(EdgeType.KNOWS)
                .weight(2)
                .build();

        when(nodeRepository.findById(goalId)).thenReturn(Optional.of(goalNode));
        when(nodeRepository.findByUserId(testUser.getId())).thenReturn(nodes);
        when(edgeRepository.findBySourceNode_User_Id(testUser.getId())).thenReturn(List.of(firstEdge, secondEdge));

        GoalPathSuggestionResponse response = nodeService.getGoalPathSuggestions(goalId, testUser, 3, 3);

        assertNotNull(response);
        assertEquals(goalId, response.getGoalId());
        assertEquals(1, response.getSuggestions().size());
        GoalPathSuggestionResponse.PathSuggestion suggestion = response.getSuggestions().get(0);
        assertEquals("Bora", suggestion.getPerson().getName());
        assertEquals(2, suggestion.getDistance());
        assertEquals(3, suggestion.getPathNodeIds().size());
        verify(nodeRepository).findByUserId(testUser.getId());
        verify(edgeRepository).findBySourceNode_User_Id(testUser.getId());
    }
}
