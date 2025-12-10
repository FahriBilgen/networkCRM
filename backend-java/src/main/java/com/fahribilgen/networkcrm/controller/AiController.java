package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.GoalSuggestionResponse;
import com.fahribilgen.networkcrm.payload.LinkPersonToGoalRequest;
import com.fahribilgen.networkcrm.payload.EdgeResponse;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import com.fahribilgen.networkcrm.service.RecommendationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/ai")
public class AiController {

    @Autowired
    private RecommendationService recommendationService;

    @Autowired
    private UserRepository userRepository;

    @GetMapping("/goals/{goalId}/suggestions")
    public ResponseEntity<GoalSuggestionResponse> getGoalSuggestions(@PathVariable UUID goalId,
                                                                     @RequestParam(defaultValue = "5") int limit,
                                                                     @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(recommendationService.suggestPeopleForGoal(goalId, limit, getUser(currentUser)));
    }

    @PostMapping("/goals/{goalId}/link-person")
    public ResponseEntity<EdgeResponse> linkPersonToGoal(@PathVariable UUID goalId,
                                                         @RequestBody LinkPersonToGoalRequest request,
                                                         @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(recommendationService.linkPersonToGoal(goalId, request, getUser(currentUser)));
    }

    private User getUser(UserPrincipal userPrincipal) {
        return userRepository.findById(userPrincipal.getId())
                .orElseThrow(() -> new RuntimeException("User not found"));
    }
}
