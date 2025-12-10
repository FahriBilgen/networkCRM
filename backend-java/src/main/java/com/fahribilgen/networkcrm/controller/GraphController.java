package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.GraphResponse;
import com.fahribilgen.networkcrm.payload.VisionTreeResponse;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import com.fahribilgen.networkcrm.service.GraphService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/graph")
public class GraphController {

    @Autowired
    private GraphService graphService;

    @Autowired
    private UserRepository userRepository;

    @GetMapping
    public ResponseEntity<GraphResponse> getGraph(@AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(graphService.getGraph(getUser(currentUser)));
    }

    @GetMapping("/vision-tree")
    public ResponseEntity<VisionTreeResponse> getVisionTree(@AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(graphService.getVisionTree(getUser(currentUser)));
    }

    private User getUser(UserPrincipal userPrincipal) {
        return userRepository.findById(userPrincipal.getId())
                .orElseThrow(() -> new RuntimeException("User not found"));
    }
}
