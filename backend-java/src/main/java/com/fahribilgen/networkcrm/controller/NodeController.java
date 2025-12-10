package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import com.fahribilgen.networkcrm.service.NodeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/nodes")
public class NodeController {

    @Autowired
    private NodeService nodeService;

    @Autowired
    private UserRepository userRepository;

    @PostMapping
    public ResponseEntity<NodeResponse> createNode(@RequestBody NodeRequest nodeRequest, @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.createNode(nodeRequest, getUser(currentUser)));
    }

    @PutMapping("/{id}")
    public ResponseEntity<NodeResponse> updateNode(@PathVariable UUID id, @RequestBody NodeRequest nodeRequest, @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.updateNode(id, nodeRequest, getUser(currentUser)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteNode(@PathVariable UUID id, @AuthenticationPrincipal UserPrincipal currentUser) {
        nodeService.deleteNode(id, getUser(currentUser));
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{id}")
    public ResponseEntity<NodeResponse> getNode(@PathVariable UUID id, @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.getNode(id, getUser(currentUser)));
    }

    @GetMapping
    public ResponseEntity<List<NodeResponse>> getAllNodes(@AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.getAllNodes(getUser(currentUser)));
    }

    @GetMapping("/search")
    public ResponseEntity<List<NodeResponse>> searchNodes(@RequestParam String query, @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.findSimilarNodes(query, getUser(currentUser)));
    }

    private User getUser(UserPrincipal userPrincipal) {
        return userRepository.findById(userPrincipal.getId())
                .orElseThrow(() -> new RuntimeException("User not found"));
    }
}
