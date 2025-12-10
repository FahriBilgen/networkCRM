package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.NodeFilterRequest;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import com.fahribilgen.networkcrm.service.NodeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.Arrays;
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

    @GetMapping("/filter")
    public ResponseEntity<List<NodeResponse>> filterNodes(@RequestParam(required = false) NodeType type,
                                                          @RequestParam(required = false, name = "types") List<String> typesParam,
                                                          @RequestParam(required = false) String sector,
                                                          @RequestParam(required = false) List<String> tags,
                                                          @RequestParam(required = false, name = "minRelationshipStrength") Integer minStrength,
                                                          @RequestParam(required = false, name = "maxRelationshipStrength") Integer maxStrength,
                                                          @RequestParam(required = false, name = "q") String searchTerm,
                                                          @AuthenticationPrincipal UserPrincipal currentUser) {
        List<NodeType> types = convertToNodeTypes(typesParam);
        List<String> normalizedTags = normalizeStringList(tags);

        NodeFilterRequest filter = NodeFilterRequest.builder()
                .type(type)
                .types(types)
                .sector(normalizeString(sector))
                .tags(normalizedTags)
                .minRelationshipStrength(minStrength)
                .maxRelationshipStrength(maxStrength)
                .searchTerm(normalizeString(searchTerm))
                .build();

        return ResponseEntity.ok(nodeService.filterNodes(filter, getUser(currentUser)));
    }

    @GetMapping("/search")
    public ResponseEntity<List<NodeResponse>> searchNodes(@RequestParam String query, @AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(nodeService.findSimilarNodes(query, getUser(currentUser)));
    }

    private User getUser(UserPrincipal userPrincipal) {
        return userRepository.findById(userPrincipal.getId())
                .orElseThrow(() -> new RuntimeException("User not found"));
    }

    private List<NodeType> convertToNodeTypes(List<String> rawTypes) {
        List<String> normalized = normalizeStringList(rawTypes);
        if (normalized == null) {
            return null;
        }
        List<NodeType> result = new ArrayList<>();
        for (String value : normalized) {
            try {
                result.add(NodeType.valueOf(value.toUpperCase()));
            } catch (IllegalArgumentException ignored) {
            }
        }
        return result.isEmpty() ? null : result;
    }

    private List<String> normalizeStringList(List<String> values) {
        if (values == null) {
            return null;
        }
        List<String> normalized = new ArrayList<>();
        for (String entry : values) {
            if (entry == null) {
                continue;
            }
            String[] split = entry.split(",");
            Arrays.stream(split)
                    .map(String::trim)
                    .filter(token -> !token.isEmpty())
                    .forEach(normalized::add);
        }
        return normalized.isEmpty() ? null : normalized;
    }

    private String normalizeString(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
