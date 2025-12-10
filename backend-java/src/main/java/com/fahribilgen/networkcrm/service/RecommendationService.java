package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.GoalSuggestionResponse;
import com.fahribilgen.networkcrm.payload.LinkPersonToGoalRequest;
import com.fahribilgen.networkcrm.payload.EdgeResponse;

import java.util.UUID;

public interface RecommendationService {
    GoalSuggestionResponse suggestPeopleForGoal(UUID goalId, int limit, User user);
    EdgeResponse linkPersonToGoal(UUID goalId, LinkPersonToGoalRequest request, User user);
}
