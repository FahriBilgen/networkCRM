package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.GoalNetworkDiagnosticsResponse;
import com.fahribilgen.networkcrm.payload.NodeClassificationRequest;
import com.fahribilgen.networkcrm.payload.NodeClassificationResponse;
import com.fahribilgen.networkcrm.payload.NodeSectorSuggestionRequest;
import com.fahribilgen.networkcrm.payload.NodeSectorSuggestionResponse;
import com.fahribilgen.networkcrm.payload.RelationshipNudgeResponse;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.impl.RecommendationServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RecommendationServiceImplTest {

    @Mock
    private NodeRepository nodeRepository;

    @Mock
    private EdgeRepository edgeRepository;

    @Mock
    private EdgeService edgeService;

    @Mock
    private EmbeddingService embeddingService;

    @InjectMocks
    private RecommendationServiceImpl recommendationService;

    private NodeClassificationRequest.NodeClassificationRequestBuilder baseRequest;

    @BeforeEach
    void setUp() {
        baseRequest = NodeClassificationRequest.builder()
                .name("2025 Growth Goal")
                .description("Objective: reach $5M ARR and launch fintech integrations.")
                .dueDate(LocalDate.now().plusMonths(6))
                .priority(4);
    }

    @Test
    void shouldClassifyVisionWhenNameHintsExist() {
        NodeClassificationRequest request = baseRequest
                .name("North Star Vision 2030")
                .description("Uzun vadeli stratejik hedefler ve neden buradayiz?")
                .priority(1)
                .build();

        NodeClassificationResponse response = recommendationService.classifyNodeCandidate(request, null);

        assertEquals(NodeType.VISION, response.getSuggestedType());
        assertTrue(response.getConfidence() > 0);
        assertTrue(response.getMatchedSignals().stream().anyMatch(signal -> signal.toLowerCase().contains("vizyon")));
    }

    @Test
    void shouldClassifyProjectWhenExecutionSignalsDetected() {
        NodeClassificationRequest request = baseRequest
                .name("Launch Campaign Projesi")
                .description("Implementation sprint to build onboarding, launch and deliver pilot.")
                .startDate(LocalDate.now())
                .dueDate(LocalDate.now().plusWeeks(4))
                .status("DOING")
                .build();

        NodeClassificationResponse response = recommendationService.classifyNodeCandidate(request, null);

        assertEquals(NodeType.PROJECT, response.getSuggestedType());
        assertTrue(response.getMatchedSignals().stream().anyMatch(signal -> signal.toLowerCase().contains("proje")));
    }

    @Test
    void shouldSuggestSectorBasedOnKeywords() {
        NodeSectorSuggestionRequest request = NodeSectorSuggestionRequest.builder()
                .name("Yeni Fintech Platformu")
                .description("Payments ve banking entegrasyonlari ile B2B POS cozumu")
                .build();

        NodeSectorSuggestionResponse response = recommendationService.suggestSector(request, null);

        assertEquals("Fintech", response.getSector());
        assertTrue(response.getConfidence() > 0);
        assertTrue(response.getMatchedKeywords().stream().anyMatch(keyword -> keyword.toLowerCase().contains("payment")));
    }

    @Test
    void shouldBuildGoalDiagnosticsFromSupports() {
        UUID userId = UUID.randomUUID();
        UUID goalId = UUID.randomUUID();

        User user = User.builder().id(userId).email("test@example.com").passwordHash("secret").build();
        Node goal = Node.builder().id(goalId).type(NodeType.GOAL).user(user).build();
        Node personStrong = Node.builder()
                .id(UUID.randomUUID())
                .type(NodeType.PERSON)
                .name("Ahmet")
                .sector("Fintech")
                .user(user)
                .build();
        Node personWeak = Node.builder()
                .id(UUID.randomUUID())
                .type(NodeType.PERSON)
                .name("Deniz")
                .sector("Marketing")
                .user(user)
                .build();
        Node personUncovered = Node.builder()
                .id(UUID.randomUUID())
                .type(NodeType.PERSON)
                .sector("AI")
                .user(user)
                .build();

        Edge strongEdge = Edge.builder()
                .id(UUID.randomUUID())
                .type(EdgeType.SUPPORTS)
                .sourceNode(personStrong)
                .targetNode(goal)
                .relationshipStrength(5)
                .lastInteractionDate(LocalDate.now().minusDays(10))
                .build();
        Edge weakEdge = Edge.builder()
                .id(UUID.randomUUID())
                .type(EdgeType.SUPPORTS)
                .sourceNode(personWeak)
                .targetNode(goal)
                .relationshipStrength(2)
                .lastInteractionDate(LocalDate.now().minusDays(120))
                .build();

        when(nodeRepository.findById(goalId)).thenReturn(Optional.of(goal));
        when(edgeRepository.findByTargetNodeId(goalId)).thenReturn(List.of(strongEdge, weakEdge));
        when(nodeRepository.findByUserId(userId)).thenReturn(List.of(goal, personStrong, personWeak, personUncovered));

        GoalNetworkDiagnosticsResponse response = recommendationService.getGoalNetworkDiagnostics(goalId, user);

        assertEquals(goalId, response.getGoalId());
        assertEquals("medium", response.getReadiness().getLevel());
        assertTrue(response.getReadiness().getSummary().stream().anyMatch(line -> line.contains("2 baglanti")));
        assertTrue(response.getSectorHighlights().get(0).toLowerCase().contains("fintech"));
        assertTrue(response.getRiskAlerts().stream().anyMatch(alert -> alert.toLowerCase().contains("iletisim yok")));
    }

    @Test
    void shouldReturnRelationshipNudgesForStaleEdges() {
        UUID userId = UUID.randomUUID();
        User user = User.builder().id(userId).email("owner@example.com").passwordHash("secret").build();
        Node person = Node.builder()
                .id(UUID.randomUUID())
                .type(NodeType.PERSON)
                .name("Bora")
                .user(user)
                .build();
        Node target = Node.builder()
                .id(UUID.randomUUID())
                .type(NodeType.GOAL)
                .name("Series A")
                .user(user)
                .build();
        Edge edge = Edge.builder()
                .id(UUID.randomUUID())
                .type(EdgeType.SUPPORTS)
                .sourceNode(person)
                .targetNode(target)
                .relationshipStrength(2)
                .lastInteractionDate(LocalDate.now().minusDays(120))
                .build();

        when(edgeRepository.findBySourceNode_User_Id(userId)).thenReturn(List.of(edge));

        RelationshipNudgeResponse response = recommendationService.getRelationshipNudges(user, 5);

        assertEquals(1, response.getNudges().size());
        RelationshipNudgeResponse.Nudge nudge = response.getNudges().get(0);
        assertEquals("Bora", nudge.getPerson().getName());
        assertTrue(nudge.getReasons().stream().anyMatch(reason -> reason.contains("iletisim")));
        assertTrue(nudge.getReasons().stream().anyMatch(reason -> reason.contains("Iliski gucu")));
    }
}
