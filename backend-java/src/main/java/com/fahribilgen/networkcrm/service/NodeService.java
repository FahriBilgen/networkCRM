package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.GoalPathSuggestionResponse;
import com.fahribilgen.networkcrm.payload.NodeFilterRequest;
import com.fahribilgen.networkcrm.payload.NodeImportResponse;
import com.fahribilgen.networkcrm.payload.NodeProximityResponse;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

public interface NodeService {
    NodeResponse createNode(NodeRequest nodeRequest, User user);
    NodeResponse updateNode(UUID nodeId, NodeRequest nodeRequest, User user);
    void deleteNode(UUID nodeId, User user);
    NodeResponse getNode(UUID nodeId, User user);
    List<NodeResponse> getAllNodes(User user);
    List<NodeResponse> getNodesByType(NodeType type, User user);
    List<NodeResponse> filterNodes(NodeFilterRequest filter, User user);
    List<NodeResponse> findSimilarNodes(String query, User user);
    NodeProximityResponse getNodeProximity(UUID nodeId, User user);
    NodeImportResponse importPersonsFromCsv(MultipartFile file, User user);
    GoalPathSuggestionResponse getGoalPathSuggestions(UUID goalId, User user, Integer maxDepth, Integer limit);
}
