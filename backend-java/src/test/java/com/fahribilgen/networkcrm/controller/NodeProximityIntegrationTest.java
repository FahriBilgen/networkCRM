package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
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

import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class NodeProximityIntegrationTest {

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
    private UUID goalId;
    private UUID personId;

    @BeforeEach
    void setUp() {
        edgeRepository.deleteAll();
        nodeRepository.deleteAll();
        userRepository.deleteAll();

        testUser = userRepository.save(User.builder()
                .email("proximity@example.com")
                .passwordHash(passwordEncoder.encode("password123"))
                .build());

        UserPrincipal principal = UserPrincipal.create(testUser);
        bearerToken = "Bearer " + jwtTokenProvider.generateToken(
                new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities()));

        goalId = nodeRepository.save(Node.builder()
                .user(testUser)
                .type(NodeType.GOAL)
                .name("Goal Node")
                .build()).getId();

        personId = nodeRepository.save(Node.builder()
                .user(testUser)
                .type(NodeType.PERSON)
                .name("Person Node")
                .relationshipStrength(4)
                .build()).getId();

        edgeRepository.save(Edge.builder()
                .sourceNode(nodeRepository.getReferenceById(personId))
                .targetNode(nodeRepository.getReferenceById(goalId))
                .type(EdgeType.SUPPORTS)
                .weight(4)
                .relationshipStrength(4)
                .build());
    }

    @Test
    void goalProximityListsSupportConnection() throws Exception {
        mockMvc.perform(get("/api/nodes/" + goalId + "/proximity")
                        .header("Authorization", bearerToken)
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.nodeId").value(goalId.toString()))
                .andExpect(jsonPath("$.totalConnections").value(1))
                .andExpect(jsonPath("$.connectionCounts.SUPPORTS").value(1))
                .andExpect(jsonPath("$.neighbors", hasSize(1)))
                .andExpect(jsonPath("$.neighbors[0].neighbor.id").value(personId.toString()))
                .andExpect(jsonPath("$.neighbors[0].outgoing").value(false));
    }
}
