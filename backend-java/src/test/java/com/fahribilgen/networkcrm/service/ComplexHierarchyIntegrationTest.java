package com.fahribilgen.networkcrm.service;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.EdgeRequest;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.repository.UserRepository;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
public class ComplexHierarchyIntegrationTest {

    @Autowired
    private NodeService nodeService;

    @Autowired
    private EdgeService edgeService;

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EdgeRepository edgeRepository;

    @Autowired
    private UserRepository userRepository;

    private User testUser;

    @BeforeEach
    void setUp() {
        testUser = User.builder()
                .email("hierarchy-test@example.com")
                .passwordHash("hashed_password")
                .build();
        userRepository.save(testUser);
    }

    @Test
    void shouldCreateFullHierarchyAndVerifyPaths() {
        // 1. Create Vision
        NodeRequest visionReq = new NodeRequest();
        visionReq.setType(NodeType.VISION);
        visionReq.setName("Global Expansion 2030");
        visionReq.setDescription("Become a global leader in fintech.");
        NodeResponse vision = nodeService.createNode(visionReq, testUser);

        // 2. Create Goal
        NodeRequest goalReq = new NodeRequest();
        goalReq.setType(NodeType.GOAL);
        goalReq.setName("Enter European Market");
        goalReq.setDescription("Establish presence in UK and Germany.");
        NodeResponse goal = nodeService.createNode(goalReq, testUser);

        // 3. Link Goal -> Vision (BELONGS_TO)
        EdgeRequest edge1 = new EdgeRequest();
        edge1.setSourceNodeId(goal.getId());
        edge1.setTargetNodeId(vision.getId());
        edge1.setType(EdgeType.BELONGS_TO);
        edge1.setWeight(5);
        edge1.setSortOrder(1);
        edgeService.createEdge(edge1, testUser);

        // 4. Create Project
        NodeRequest projectReq = new NodeRequest();
        projectReq.setType(NodeType.PROJECT);
        projectReq.setName("UK License Application");
        projectReq.setDescription("Apply for FCA license.");
        NodeResponse project = nodeService.createNode(projectReq, testUser);

        // 5. Link Project -> Goal (BELONGS_TO)
        EdgeRequest edge2 = new EdgeRequest();
        edge2.setSourceNodeId(project.getId());
        edge2.setTargetNodeId(goal.getId());
        edge2.setType(EdgeType.BELONGS_TO);
        edge2.setWeight(5);
        edge2.setSortOrder(1);
        edgeService.createEdge(edge2, testUser);

        // 6. Create Person
        NodeRequest personReq = new NodeRequest();
        personReq.setType(NodeType.PERSON);
        personReq.setName("Legal Consultant");
        personReq.setDescription("Expert in UK financial regulations.");
        NodeResponse person = nodeService.createNode(personReq, testUser);

        // 7. Link Person -> Project (SUPPORTS)
        EdgeRequest edge3 = new EdgeRequest();
        edge3.setSourceNodeId(person.getId());
        edge3.setTargetNodeId(project.getId());
        edge3.setType(EdgeType.SUPPORTS);
        edge3.setWeight(4);
        edgeService.createEdge(edge3, testUser);

        // --- Verification ---
        // Verify Nodes exist
        assertTrue(nodeRepository.existsById(vision.getId()));
        assertTrue(nodeRepository.existsById(goal.getId()));
        assertTrue(nodeRepository.existsById(project.getId()));
        assertTrue(nodeRepository.existsById(person.getId()));

        // Verify Edges exist
        List<Edge> edges = edgeRepository.findAll();
        assertEquals(3, edges.size());

        // Verify Hierarchy Path: Person -> Project -> Goal -> Vision
        // We can check this by querying edges
        Edge personToProject = edgeRepository.findFirstBySourceNodeIdAndTargetNodeIdAndType(
                person.getId(), project.getId(), EdgeType.SUPPORTS).orElseThrow();
        assertNotNull(personToProject);

        Edge projectToGoal = edgeRepository.findFirstBySourceNodeIdAndTargetNodeIdAndType(
                project.getId(), goal.getId(), EdgeType.BELONGS_TO).orElseThrow();
        assertNotNull(projectToGoal);

        Edge goalToVision = edgeRepository.findFirstBySourceNodeIdAndTargetNodeIdAndType(
                goal.getId(), vision.getId(), EdgeType.BELONGS_TO).orElseThrow();
        assertNotNull(goalToVision);

        // Verify weights
        assertEquals(4, personToProject.getWeight());
        assertEquals(5, goalToVision.getWeight());
    }
}
