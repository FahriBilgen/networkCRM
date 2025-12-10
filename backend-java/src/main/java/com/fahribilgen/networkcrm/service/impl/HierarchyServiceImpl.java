package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.EdgeRequest;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.EdgeService;
import com.fahribilgen.networkcrm.service.HierarchyService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
public class HierarchyServiceImpl implements HierarchyService {

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EdgeRepository edgeRepository;

    @Autowired
    private EdgeService edgeService;

    @Override
    @Transactional
    public void moveGoal(UUID goalId, UUID visionId, Integer sortOrder, User user) {
        Node goal = getNode(goalId);
        Node vision = getNode(visionId);

        if (goal.getType() != NodeType.GOAL) {
            throw new RuntimeException("Node " + goalId + " is not a goal");
        }
        if (vision.getType() != NodeType.VISION) {
            throw new RuntimeException("Target node is not a vision");
        }
        validateOwnership(goal, user);
        validateOwnership(vision, user);

        replaceBelongsToEdge(goalId, sortOrder, visionId, user);
    }

    @Override
    @Transactional
    public void moveProject(UUID projectId, UUID goalId, Integer sortOrder, User user) {
        Node project = getNode(projectId);
        Node goal = getNode(goalId);

        if (project.getType() != NodeType.PROJECT) {
            throw new RuntimeException("Node " + projectId + " is not a project");
        }
        if (goal.getType() != NodeType.GOAL) {
            throw new RuntimeException("Target node is not a goal");
        }
        validateOwnership(project, user);
        validateOwnership(goal, user);

        replaceBelongsToEdge(projectId, sortOrder, goalId, user);
    }

    private void replaceBelongsToEdge(UUID sourceNodeId, Integer sortOrder, UUID targetNodeId, User user) {
        List<Edge> existing = edgeRepository.findBySourceNodeIdAndType(sourceNodeId, EdgeType.BELONGS_TO);
        existing.forEach(edgeRepository::delete);

        EdgeRequest request = new EdgeRequest();
        request.setSourceNodeId(sourceNodeId);
        request.setTargetNodeId(targetNodeId);
        request.setType(EdgeType.BELONGS_TO);
        request.setSortOrder(sortOrder);
        request.setWeight(0);
        request.setAddedByUser(true);

        edgeService.createEdge(request, user);
    }

    private Node getNode(UUID nodeId) {
        return nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found: " + nodeId));
    }

    private void validateOwnership(Node node, User user) {
        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node " + node.getId());
        }
    }
}
