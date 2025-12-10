package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.HierarchyMoveRequest;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import com.fahribilgen.networkcrm.service.HierarchyService;
import com.fahribilgen.networkcrm.service.NodeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/goals")
public class GoalController {

    @Autowired
    private NodeService nodeService;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private HierarchyService hierarchyService;

    @PostMapping
    public ResponseEntity<NodeResponse> createGoal(@RequestBody NodeRequest request, @AuthenticationPrincipal UserPrincipal currentUser) {
        request.setType(NodeType.GOAL);
        return ResponseEntity.ok(nodeService.createNode(request, getUser(currentUser)));
    }

    @PutMapping("/{id}")
    public ResponseEntity<NodeResponse> updateGoal(@PathVariable UUID id, @RequestBody NodeRequest request, @AuthenticationPrincipal UserPrincipal currentUser) {
        request.setType(NodeType.GOAL);
        return ResponseEntity.ok(nodeService.updateNode(id, request, getUser(currentUser)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteGoal(@PathVariable UUID id, @AuthenticationPrincipal UserPrincipal currentUser) {
        nodeService.deleteNode(id, getUser(currentUser));
        return ResponseEntity.ok().build();
    }

    @GetMapping
    public ResponseEntity<List<NodeResponse>> getGoals(@AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.getNodesByType(NodeType.GOAL, getUser(currentUser)));
    }

    @GetMapping("/{id}")
    public ResponseEntity<NodeResponse> getGoal(@PathVariable UUID id, @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.getNode(id, getUser(currentUser)));
    }

    @PostMapping("/{id}/move")
    public ResponseEntity<Void> moveGoal(@PathVariable UUID id,
                                         @RequestBody HierarchyMoveRequest request,
                                         @AuthenticationPrincipal UserPrincipal currentUser) {
        if (request == null || request.getTargetNodeId() == null) {
            return ResponseEntity.badRequest().build();
        }
        hierarchyService.moveGoal(id, request.getTargetNodeId(), request.getSortOrder(), getUser(currentUser));
        return ResponseEntity.ok().build();
    }

    private User getUser(UserPrincipal userPrincipal) {
        return userRepository.findById(userPrincipal.getId())
                .orElseThrow(() -> new RuntimeException("User not found"));
    }
}
