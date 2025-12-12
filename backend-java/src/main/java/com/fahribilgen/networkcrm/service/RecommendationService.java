package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.GoalNetworkDiagnosticsResponse;
import com.fahribilgen.networkcrm.payload.GoalSuggestionResponse;
import com.fahribilgen.networkcrm.payload.LinkPersonToGoalRequest;
import com.fahribilgen.networkcrm.payload.EdgeResponse;
import com.fahribilgen.networkcrm.payload.NodeClassificationRequest;
import com.fahribilgen.networkcrm.payload.NodeClassificationResponse;
import com.fahribilgen.networkcrm.payload.NodeSectorSuggestionRequest;
import com.fahribilgen.networkcrm.payload.NodeSectorSuggestionResponse;
import com.fahribilgen.networkcrm.payload.RelationshipNudgeResponse;

import java.util.UUID;

public interface RecommendationService {
    GoalSuggestionResponse suggestPeopleForGoal(UUID goalId, int limit, User user);
    EdgeResponse linkPersonToGoal(UUID goalId, LinkPersonToGoalRequest request, User user);
    NodeClassificationResponse classifyNodeCandidate(NodeClassificationRequest request, User user);
    NodeSectorSuggestionResponse suggestSector(NodeSectorSuggestionRequest request, User user);
    GoalNetworkDiagnosticsResponse getGoalNetworkDiagnostics(UUID goalId, User user);
    RelationshipNudgeResponse getRelationshipNudges(User user, int limit);
}
