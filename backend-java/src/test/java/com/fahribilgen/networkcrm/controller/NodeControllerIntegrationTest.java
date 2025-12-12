package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.NodeImportResponse;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import com.fahribilgen.networkcrm.service.NodeService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.multipart.MultipartFile;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class NodeControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private NodeService nodeService;

    @MockBean
    private UserRepository userRepository;

    private NodeResponse testNodeResponse;
    private NodeRequest nodeRequest;
    private User testUser;

    @BeforeEach
    void setUp() {
        testUser = User.builder()
                .id(UUID.randomUUID())
                .email("test@example.com")
                .build();

        testNodeResponse = NodeResponse.builder()
                .id(UUID.randomUUID())
                .type(NodeType.PERSON)
                .name("John Doe")
                .description("Test person")
                .sector("Technology")
                .tags(Arrays.asList("tech", "ai"))
                .relationshipStrength(5)
                .properties(Map.of(
                        "timeline",
                        List.of(Map.of("id", "entry-1", "date", "2025-01-01", "note", "Kickoff"))
                ))
                .build();

        nodeRequest = NodeRequest.builder()
                .type(NodeType.PERSON)
                .name("John Doe")
                .description("Test person")
                .sector("Technology")
                .tags(Arrays.asList("tech", "ai"))
                .relationshipStrength(5)
                .build();

        when(userRepository.findById(any(UUID.class)))
                .thenAnswer(invocation -> Optional.of(testUser));
    }

    private void authenticate() {
        UserPrincipal principal = UserPrincipal.create(testUser);
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities())
        );
    }

    @Test
    void testCreateNode_Success() throws Exception {
        authenticate();
        when(nodeService.createNode(any(NodeRequest.class), any(User.class)))
                .thenReturn(testNodeResponse);

        mockMvc.perform(post("/api/nodes")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(nodeRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("John Doe"))
                .andExpect(jsonPath("$.type").value("PERSON"))
                .andExpect(jsonPath("$.sector").value("Technology"));
    }

    @Test
    void testGetNode_Success() throws Exception {
        authenticate();
        UUID nodeId = testNodeResponse.getId();
        when(nodeService.getNode(eq(nodeId), any(User.class)))
                .thenReturn(testNodeResponse);

        mockMvc.perform(get("/api/nodes/" + nodeId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(nodeId.toString()))
                .andExpect(jsonPath("$.name").value("John Doe"));
    }

    @Test
    void testUpdateNode_Success() throws Exception {
        authenticate();
        UUID nodeId = testNodeResponse.getId();
        NodeRequest updateRequest = NodeRequest.builder()
                .type(NodeType.PERSON)
                .name("Jane Doe")
                .sector("Finance")
                .build();

        NodeResponse updatedResponse = NodeResponse.builder()
                .id(nodeId)
                .type(NodeType.PERSON)
                .name("Jane Doe")
                .sector("Finance")
                .build();

        when(nodeService.updateNode(eq(nodeId), any(NodeRequest.class), any(User.class)))
                .thenReturn(updatedResponse);

        mockMvc.perform(put("/api/nodes/" + nodeId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updateRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Jane Doe"))
                .andExpect(jsonPath("$.sector").value("Finance"));
    }

    @Test
    void testUpdateNode_ReturnsProperties() throws Exception {
        authenticate();
        UUID nodeId = testNodeResponse.getId();
        NodeResponse updatedResponse = NodeResponse.builder()
                .id(nodeId)
                .type(NodeType.PERSON)
                .name("Timeline Owner")
                .properties(Map.of(
                        "timeline",
                        List.of(Map.of("id", "entry-2", "date", "2025-02-01", "note", "Mentor call"))
                ))
                .build();

        when(nodeService.updateNode(eq(nodeId), any(NodeRequest.class), any(User.class)))
                .thenReturn(updatedResponse);

        mockMvc.perform(put("/api/nodes/" + nodeId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(nodeRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.properties.timeline[0].note").value("Mentor call"));
    }

    @Test
    void testDeleteNode_Success() throws Exception {
        authenticate();
        UUID nodeId = testNodeResponse.getId();

        mockMvc.perform(delete("/api/nodes/" + nodeId))
                .andExpect(status().isOk());
    }

    @Test
    void testGetAllNodes_Success() throws Exception {
        authenticate();
        when(nodeService.getAllNodes(any(User.class)))
                .thenReturn(Arrays.asList(testNodeResponse));

        mockMvc.perform(get("/api/nodes"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].name").value("John Doe"))
                .andExpect(jsonPath("$[0].type").value("PERSON"));
    }

    @Test
    void testCreateNode_Unauthorized() throws Exception {
        SecurityContextHolder.clearContext();
        mockMvc.perform(post("/api/nodes")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(nodeRequest)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void testImportCsv() throws Exception {
        authenticate();
        MockMultipartFile file = new MockMultipartFile("file", "contacts.csv", "text/csv", "name\nJohn Doe".getBytes());
        NodeImportResponse response = NodeImportResponse.builder()
                .processed(1)
                .created(1)
                .skipped(0)
                .errors(List.of())
                .build();
        when(nodeService.importPersonsFromCsv(any(MultipartFile.class), any(User.class))).thenReturn(response);

        mockMvc.perform(multipart("/api/nodes/import/csv").file(file))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.created").value(1));
    }

}
