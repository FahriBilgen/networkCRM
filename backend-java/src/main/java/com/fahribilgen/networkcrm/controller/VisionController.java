package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.NodeType;
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
@RequestMapping("/api/visions")
public class VisionController {

    @Autowired
    private NodeService nodeService;

    @Autowired
    private UserRepository userRepository;

    @PostMapping
    public ResponseEntity<NodeResponse> createVision(@RequestBody NodeRequest request, @AuthenticationPrincipal UserPrincipal currentUser) {
        request.setType(NodeType.VISION);
        return ResponseEntity.ok(nodeService.createNode(request, getUser(currentUser)));
    }

    @PutMapping("/{id}")
    public ResponseEntity<NodeResponse> updateVision(@PathVariable UUID id, @RequestBody NodeRequest request, @AuthenticationPrincipal UserPrincipal currentUser) {
        request.setType(NodeType.VISION);
        return ResponseEntity.ok(nodeService.updateNode(id, request, getUser(currentUser)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteVision(@PathVariable UUID id, @AuthenticationPrincipal UserPrincipal currentUser) {
        nodeService.deleteNode(id, getUser(currentUser));
        return ResponseEntity.ok().build();
    }

    @GetMapping
    public ResponseEntity<List<NodeResponse>> getVisions(@AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.getNodesByType(NodeType.VISION, getUser(currentUser)));
    }

    @GetMapping("/{id}")
    public ResponseEntity<NodeResponse> getVision(@PathVariable UUID id, @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.getNode(id, getUser(currentUser)));
    }

    private User getUser(UserPrincipal userPrincipal) {
        return userRepository.findById(userPrincipal.getId())
                .orElseThrow(() -> new RuntimeException("User not found"));
    }
}
