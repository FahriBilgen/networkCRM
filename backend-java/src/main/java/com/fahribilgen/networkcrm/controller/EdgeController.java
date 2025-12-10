package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.EdgeRequest;
import com.fahribilgen.networkcrm.payload.EdgeResponse;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import com.fahribilgen.networkcrm.service.EdgeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/edges")
public class EdgeController {

    @Autowired
    private EdgeService edgeService;

    @Autowired
    private UserRepository userRepository;

    @PostMapping
    public ResponseEntity<EdgeResponse> createEdge(@RequestBody EdgeRequest edgeRequest, @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(edgeService.createEdge(edgeRequest, getUser(currentUser)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteEdge(@PathVariable UUID id, @AuthenticationPrincipal UserPrincipal currentUser) {
        edgeService.deleteEdge(id, getUser(currentUser));
        return ResponseEntity.ok().build();
    }

    @GetMapping("/node/{nodeId}")
    public ResponseEntity<List<EdgeResponse>> getEdgesForNode(@PathVariable UUID nodeId, @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(edgeService.getEdgesForNode(nodeId, getUser(currentUser)));
    }

    private User getUser(UserPrincipal userPrincipal) {
        return userRepository.findById(userPrincipal.getId())
                .orElseThrow(() -> new RuntimeException("User not found"));
    }
}
