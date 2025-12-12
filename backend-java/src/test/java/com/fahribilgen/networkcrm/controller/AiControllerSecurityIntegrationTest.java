package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.JwtTokenProvider;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AiControllerSecurityIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EdgeRepository edgeRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    private User testUser;
    private String bearerToken;
    private UUID personId;
    private UUID goalId;

    @BeforeEach
    void setUp() {
        edgeRepository.deleteAll();
        nodeRepository.deleteAll();
        userRepository.deleteAll();

        testUser = userRepository.save(User.builder()
                .email("aiuser@example.com")
                .passwordHash(passwordEncoder.encode("password123"))
                .build());

        UserPrincipal principal = UserPrincipal.create(testUser);
        bearerToken = "Bearer " + jwtTokenProvider.generateToken(
                new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities()));

        personId = nodeRepository.save(Node.builder()
                .user(testUser)
                .type(NodeType.PERSON)
                .name("AI Person")
                .relationshipStrength(3)
                .build()).getId();

        goalId = nodeRepository.save(Node.builder()
                .user(testUser)
                .type(NodeType.GOAL)
                .name("AI Goal")
                .build()).getId();
    }

    @Test
    void linkPersonToGoalCreatesSupportEdge() throws Exception {
        String payload = """
                {
                  "personId": "%s",
                  "relationshipStrength": 4,
                  "notes": "automated test",
                  "relevanceScore": 0.8
                }
                """.formatted(personId);

        mockMvc.perform(post("/api/ai/goals/" + goalId + "/link-person")
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("Authorization", bearerToken)
                        .content(payload))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sourceNodeId").value(personId.toString()))
                .andExpect(jsonPath("$.targetNodeId").value(goalId.toString()))
                .andExpect(jsonPath("$.relationshipStrength").value(4));

        Edge saved = edgeRepository.findBySourceNodeId(personId).stream()
                .filter(edge -> goalId.equals(edge.getTargetNode().getId()))
                .findFirst()
                .orElse(null);
        assertNotNull(saved);
        assertEquals(4, saved.getRelationshipStrength());
    }
}
