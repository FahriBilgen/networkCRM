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

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class NodeControllerSecurityIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EdgeRepository edgeRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    private User testUser;
    private String bearerToken;

    @BeforeEach
    void setUp() {
        edgeRepository.deleteAll();
        nodeRepository.deleteAll();
        userRepository.deleteAll();

        testUser = User.builder()
                .email("secureuser@example.com")
                .passwordHash(passwordEncoder.encode("password123"))
                .build();
        testUser = userRepository.save(testUser);

        UserPrincipal principal = UserPrincipal.create(testUser);
        UsernamePasswordAuthenticationToken authentication =
                new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities());
        bearerToken = "Bearer " + jwtTokenProvider.generateToken(authentication);
    }

    private Node createNode(NodeType type, String name) {
        return nodeRepository.save(Node.builder()
                .user(testUser)
                .type(type)
                .name(name)
                .build());
    }

    @Test
    void deleteNodeRemovesConnectedEdges() throws Exception {
        Node person = createNode(NodeType.PERSON, "Secure Person");
        Node goal = createNode(NodeType.GOAL, "Secure Goal");

        edgeRepository.save(Edge.builder()
                .sourceNode(person)
                .targetNode(goal)
                .type(EdgeType.SUPPORTS)
                .weight(3)
                .relationshipStrength(3)
                .build());

        mockMvc.perform(delete("/api/nodes/" + goal.getId())
                .header("Authorization", bearerToken)
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());

        assertThat(nodeRepository.findById(goal.getId())).isEmpty();
        assertThat(edgeRepository.findByTargetNodeId(goal.getId())).isEmpty();

        mockMvc.perform(delete("/api/nodes/" + person.getId())
                .header("Authorization", bearerToken)
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());

        assertThat(nodeRepository.findById(person.getId())).isEmpty();
        assertThat(edgeRepository.findBySourceNodeId(person.getId())).isEmpty();
    }
}
