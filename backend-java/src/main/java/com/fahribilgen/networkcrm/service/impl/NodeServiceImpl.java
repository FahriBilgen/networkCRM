package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.GoalPathSuggestionResponse;
import com.fahribilgen.networkcrm.payload.NodeFilterRequest;
import com.fahribilgen.networkcrm.payload.NodeImportResponse;
import com.fahribilgen.networkcrm.payload.NodeProximityResponse;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.EmbeddingService;
import com.fahribilgen.networkcrm.service.NodeService;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import jakarta.persistence.criteria.Join;
import jakarta.persistence.criteria.JoinType;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.Root;
import jakarta.persistence.criteria.Subquery;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ResponseStatusException;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.web.multipart.MultipartFile;

@Service
public class NodeServiceImpl implements NodeService {

    private static final Logger logger = LoggerFactory.getLogger(NodeServiceImpl.class);
    private static final String[] NAME_COLUMNS = {"name", "full name", "full_name"};
    private static final String[] FIRST_NAME_COLUMNS = {"first name", "first_name", "first"};
    private static final String[] LAST_NAME_COLUMNS = {"last name", "last_name", "last"};
    private static final String[] COMPANY_COLUMNS = {"company", "organization", "current company"};
    private static final String[] ROLE_COLUMNS = {"position", "headline", "title", "role"};
    private static final String[] SECTOR_COLUMNS = {"industry", "sector"};
    private static final String[] TAG_COLUMNS = {"tags", "label", "labels"};
    private static final String[] NOTES_COLUMNS = {"notes", "note"};
    private static final String[] LINKEDIN_COLUMNS = {"linkedin url", "linkedin profile url", "profile url"};

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EmbeddingService embeddingService;

    @Autowired
    private EdgeRepository edgeRepository;

    @Override
    @Transactional
    public NodeResponse createNode(NodeRequest nodeRequest, User user) {
        validateNodeRequest(nodeRequest);
        List<Double> embedding = generateEmbeddingForRequest(nodeRequest);
        Node node = Node.builder()
                .user(user)
                .type(nodeRequest.getType())
                .name(nodeRequest.getName())
                .description(nodeRequest.getDescription())
                .sector(nodeRequest.getSector())
                .tags(normalizeTags(nodeRequest.getTags()))
                .relationshipStrength(nodeRequest.getRelationshipStrength())
                .company(nodeRequest.getCompany())
                .role(nodeRequest.getRole())
                .linkedinUrl(nodeRequest.getLinkedinUrl())
                .notes(nodeRequest.getNotes())
                .priority(nodeRequest.getPriority())
                .dueDate(nodeRequest.getDueDate())
                .startDate(nodeRequest.getStartDate())
                .endDate(nodeRequest.getEndDate())
                .status(nodeRequest.getStatus())
                .properties(nodeRequest.getProperties())
                .embedding(embedding)
                .build();

        Node savedNode = nodeRepository.save(node);
        return mapToResponse(savedNode);
    }

    @Override
    @Transactional
    public NodeResponse updateNode(UUID nodeId, NodeRequest nodeRequest, User user) {
        validateNodeRequest(nodeRequest);
        Node node = nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found"));

        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node");
        }

        node.setType(nodeRequest.getType());
        node.setName(nodeRequest.getName());
        node.setDescription(nodeRequest.getDescription());
        node.setSector(nodeRequest.getSector());
        if (nodeRequest.getTags() != null) {
            node.setTags(normalizeTags(nodeRequest.getTags()));
        }
        node.setRelationshipStrength(nodeRequest.getRelationshipStrength());
        node.setCompany(nodeRequest.getCompany());
        node.setRole(nodeRequest.getRole());
        node.setLinkedinUrl(nodeRequest.getLinkedinUrl());
        node.setNotes(nodeRequest.getNotes());
        node.setPriority(nodeRequest.getPriority());
        node.setDueDate(nodeRequest.getDueDate());
        node.setStartDate(nodeRequest.getStartDate());
        node.setEndDate(nodeRequest.getEndDate());
        node.setStatus(nodeRequest.getStatus());
        node.setProperties(nodeRequest.getProperties());

        List<Double> embedding = generateEmbeddingForRequest(nodeRequest);
        if (embedding != null) {
            node.setEmbedding(embedding);
        }

        Node updatedNode = nodeRepository.save(node);
        return mapToResponse(updatedNode);
    }

    @Override
    @Transactional
    public void deleteNode(UUID nodeId, User user) {
        Node node = nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found"));

        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node");
        }

        List<Edge> outgoing = edgeRepository.findBySourceNodeId(nodeId);
        if (!CollectionUtils.isEmpty(outgoing)) {
            edgeRepository.deleteAll(outgoing);
        }

        List<Edge> incoming = edgeRepository.findByTargetNodeId(nodeId);
        if (!CollectionUtils.isEmpty(incoming)) {
            edgeRepository.deleteAll(incoming);
        }

        nodeRepository.delete(node);
    }

    @Override
    public NodeResponse getNode(UUID nodeId, User user) {
        Node node = nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found"));

        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node");
        }

        return mapToResponse(node);
    }

    @Override
    public List<NodeResponse> getAllNodes(User user) {
        List<Node> nodes = nodeRepository.findByUserId(user.getId());
        return nodes.stream().map(this::mapToResponse).collect(Collectors.toList());
    }

    @Override
    public List<NodeResponse> getNodesByType(NodeType type, User user) {
        List<Node> nodes = nodeRepository.findByUserIdAndType(user.getId(), type);
        return nodes.stream().map(this::mapToResponse).collect(Collectors.toList());
    }

    @Override
    public List<NodeResponse> filterNodes(NodeFilterRequest filter, User user) {
        Specification<Node> specification = belongsToUser(user.getId());

        if (filter == null) {
            return nodeRepository.findAll(specification).stream()
                    .map(this::mapToResponse)
                    .collect(Collectors.toList());
        }

        if (filter.getType() != null) {
            specification = specification.and(hasType(filter.getType()));
        }

        if (!CollectionUtils.isEmpty(filter.getTypes())) {
            specification = specification.and(hasAnyType(filter.getTypes()));
        }

        if (StringUtils.hasText(filter.getSector())) {
            specification = specification.and(hasSector(filter.getSector()));
        }

        if (!CollectionUtils.isEmpty(filter.getTags())) {
            Specification<Node> tagSpec = hasAllTags(filter.getTags());
            if (tagSpec != null) {
                specification = specification.and(tagSpec);
            }
        }

        if (filter.getMinRelationshipStrength() != null) {
            specification = specification.and(hasMinRelationshipStrength(filter.getMinRelationshipStrength()));
        }

        if (filter.getMaxRelationshipStrength() != null) {
            specification = specification.and(hasMaxRelationshipStrength(filter.getMaxRelationshipStrength()));
        }

        if (StringUtils.hasText(filter.getSearchTerm())) {
            specification = specification.and(containsSearchTerm(filter.getSearchTerm()));
        }

        return nodeRepository.findAll(specification).stream()
                .map(this::mapToResponse)
                .collect(Collectors.toList());
    }

    @Override
    public List<NodeResponse> findSimilarNodes(String query, User user) {
        if (query == null || query.isBlank()) {
            return List.of();
        }

        List<Double> queryEmbedding = embeddingService.generateEmbedding(query);
        if (queryEmbedding == null) {
            return List.of();
        }

        List<Node> nodes = nodeRepository.findByUserId(user.getId());

        return nodes.stream()
                .filter(node -> node.getEmbedding() != null)
                .sorted((n1, n2) -> {
                    double sim1 = cosineSimilarity(queryEmbedding, n1.getEmbedding());
                    double sim2 = cosineSimilarity(queryEmbedding, n2.getEmbedding());
                    return Double.compare(sim2, sim1); // Descending order
                })
                .limit(5)
                .map(this::mapToResponse)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional(readOnly = true)
    public NodeProximityResponse getNodeProximity(UUID nodeId, User user) {
        Node node = nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found"));

        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node");
        }

        List<NodeProximityResponse.NeighborConnection> neighbors = new ArrayList<>();
        Map<EdgeType, Long> connectionCounts = new EnumMap<>(EdgeType.class);

        List<Edge> outgoing = edgeRepository.findBySourceNodeId(nodeId);
        List<Edge> incoming = edgeRepository.findByTargetNodeId(nodeId);

        accumulateNeighbors(outgoing, neighbors, connectionCounts, true, user.getId());
        accumulateNeighbors(incoming, neighbors, connectionCounts, false, user.getId());

        double influenceScore = calculateInfluenceScore(neighbors);

        return NodeProximityResponse.builder()
                .nodeId(nodeId)
                .totalConnections(neighbors.size())
                .connectionCounts(connectionCounts)
                .neighbors(neighbors)
                .influenceScore(influenceScore)
                .build();
    }

    @Override
    @Transactional(readOnly = true)
    public GoalPathSuggestionResponse getGoalPathSuggestions(UUID goalId, User user, Integer maxDepth, Integer limit) {
        int depthLimit = maxDepth == null ? 3 : Math.max(2, Math.min(maxDepth, 6));
        int suggestionLimit = limit == null ? 3 : Math.max(1, Math.min(limit, 10));

        Node goalNode = nodeRepository.findById(goalId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Goal not found"));

        if (!goalNode.getUser().getId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Goal not accessible");
        }
        if (goalNode.getType() != NodeType.GOAL) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Path suggestions require a GOAL node.");
        }

        List<Node> nodes = nodeRepository.findByUserId(user.getId());
        if (CollectionUtils.isEmpty(nodes)) {
            return GoalPathSuggestionResponse.builder()
                    .goalId(goalId)
                    .suggestions(List.of())
                    .build();
        }

        Map<UUID, Node> nodeMap = nodes.stream()
                .collect(Collectors.toMap(Node::getId, node -> node));

        Map<UUID, Set<UUID>> adjacency = buildAdjacencyMap(nodeMap, edgeRepository.findBySourceNode_User_Id(user.getId()));
        if (!adjacency.containsKey(goalId)) {
            adjacency.put(goalId, new HashSet<>());
        }

        Deque<PathSearchState> queue = new ArrayDeque<>();
        Set<UUID> visited = new HashSet<>();
        queue.add(new PathSearchState(goalId, List.of(goalId)));
        visited.add(goalId);

        List<GoalPathSuggestionResponse.PathSuggestion> suggestions = new ArrayList<>();

        while (!queue.isEmpty()) {
            PathSearchState state = queue.removeFirst();
            int distance = state.path().size() - 1;
            if (distance > depthLimit) {
                continue;
            }

            if (!state.nodeId().equals(goalId)) {
                Node current = nodeMap.get(state.nodeId());
                if (current != null && current.getType() == NodeType.PERSON && distance >= 2) {
                    suggestions.add(GoalPathSuggestionResponse.PathSuggestion.builder()
                            .person(mapToResponse(current))
                            .distance(distance)
                            .pathNodeIds(new ArrayList<>(state.path()))
                            .build());
                    if (suggestions.size() >= suggestionLimit) {
                        break;
                    }
                }
            }

            Set<UUID> neighbors = adjacency.getOrDefault(state.nodeId(), Set.of());
            for (UUID neighborId : neighbors) {
                if (visited.add(neighborId)) {
                    List<UUID> nextPath = new ArrayList<>(state.path());
                    nextPath.add(neighborId);
                    queue.add(new PathSearchState(neighborId, nextPath));
                }
            }
        }

        return GoalPathSuggestionResponse.builder()
                .goalId(goalId)
                .suggestions(suggestions)
                .build();
    }

    @Override
    @Transactional
    public NodeImportResponse importPersonsFromCsv(MultipartFile file, User user) {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "CSV dosyasi gerekli.");
        }

        int processed = 0;
        int created = 0;
        int skipped = 0;
        List<String> errors = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            CSVParser parser = CSVFormat.DEFAULT
                    .builder()
                    .setHeader()
                    .setSkipHeaderRecord(true)
                    .setIgnoreHeaderCase(true)
                    .setIgnoreEmptyLines(true)
                    .setTrim(true)
                    .build()
                    .parse(reader);

            Map<String, String> headers = parser.getHeaderMap().keySet().stream()
                    .collect(Collectors.toMap(h -> h.toLowerCase(Locale.ROOT), h -> h, (a, b) -> a));

            for (CSVRecord record : parser) {
                processed++;
                String name = resolveName(record, headers);
                if (!StringUtils.hasText(name)) {
                    errors.add("Satir " + record.getRecordNumber() + ": isim alanı bulunamadı.");
                    skipped++;
                    continue;
                }
                if (nodeRepository.existsByUserIdAndNameIgnoreCase(user.getId(), name)) {
                    skipped++;
                    continue;
                }

                NodeRequest request = NodeRequest.builder()
                        .type(NodeType.PERSON)
                        .name(name)
                        .company(resolveValue(record, headers, COMPANY_COLUMNS))
                        .role(resolveValue(record, headers, ROLE_COLUMNS))
                        .sector(resolveValue(record, headers, SECTOR_COLUMNS))
                        .tags(parseTags(resolveValue(record, headers, TAG_COLUMNS)))
                        .notes(resolveValue(record, headers, NOTES_COLUMNS))
                        .linkedinUrl(resolveValue(record, headers, LINKEDIN_COLUMNS))
                        .relationshipStrength(parseInteger(resolveValue(record, headers, new String[]{"relationship_strength", "relationship strength"})))
                        .build();

                try {
                    createNode(request, user);
                    created++;
                } catch (Exception ex) {
                    logger.warn("Failed to import CSV record {}", record.getRecordNumber(), ex);
                    errors.add("Satir " + record.getRecordNumber() + ": " + ex.getMessage());
                    skipped++;
                }
            }
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "CSV okunamadi.", e);
        }

        return NodeImportResponse.builder()
                .processed(processed)
                .created(created)
                .skipped(skipped)
                .errors(errors)
                .build();
    }

    private Map<UUID, Set<UUID>> buildAdjacencyMap(Map<UUID, Node> nodeMap, List<Edge> edges) {
        Map<UUID, Set<UUID>> adjacency = new HashMap<>();
        nodeMap.keySet().forEach(id -> adjacency.put(id, new HashSet<>()));
        if (CollectionUtils.isEmpty(edges)) {
            return adjacency;
        }
        for (Edge edge : edges) {
            UUID sourceId = edge.getSourceNode() != null ? edge.getSourceNode().getId() : null;
            UUID targetId = edge.getTargetNode() != null ? edge.getTargetNode().getId() : null;
            if (sourceId == null || targetId == null) {
                continue;
            }
            if (!adjacency.containsKey(sourceId) || !adjacency.containsKey(targetId)) {
                continue;
            }
            adjacency.get(sourceId).add(targetId);
            adjacency.get(targetId).add(sourceId);
        }
        return adjacency;
    }

    private void accumulateNeighbors(List<Edge> edges,
                                     List<NodeProximityResponse.NeighborConnection> neighbors,
                                     Map<EdgeType, Long> connectionCounts,
                                     boolean outgoing,
                                     UUID userId) {
        if (CollectionUtils.isEmpty(edges)) {
            return;
        }
        for (Edge edge : edges) {
            Node neighborNode = outgoing ? edge.getTargetNode() : edge.getSourceNode();
            if (neighborNode == null || neighborNode.getUser() == null || !neighborNode.getUser().getId().equals(userId)) {
                continue;
            }
            connectionCounts.merge(edge.getType(), 1L, Long::sum);
            neighbors.add(NodeProximityResponse.NeighborConnection.builder()
                    .edgeId(edge.getId())
                    .edgeType(edge.getType())
                    .outgoing(outgoing)
                    .relationshipStrength(edge.getRelationshipStrength())
                    .lastInteractionDate(edge.getLastInteractionDate())
                    .neighbor(mapToResponse(neighborNode))
                    .build());
        }
    }

    private double calculateInfluenceScore(List<NodeProximityResponse.NeighborConnection> neighbors) {
        if (CollectionUtils.isEmpty(neighbors)) {
            return 0.0;
        }
        double connectionScore = neighbors.size();
        double strengthSum = neighbors.stream()
                .map(NodeProximityResponse.NeighborConnection::getRelationshipStrength)
                .filter(Objects::nonNull)
                .mapToDouble(Integer::doubleValue)
                .sum();
        double avgStrength = connectionScore == 0 ? 0 : strengthSum / connectionScore;
        return connectionScore + avgStrength;
    }

    private double cosineSimilarity(List<Double> v1, List<Double> v2) {
        if (v1 == null || v2 == null || v1.size() != v2.size()) {
            return 0.0;
        }

        double dotProduct = 0.0;
        double normA = 0.0;
        double normB = 0.0;

        for (int i = 0; i < v1.size(); i++) {
            dotProduct += v1.get(i) * v2.get(i);
            normA += Math.pow(v1.get(i), 2);
            normB += Math.pow(v2.get(i), 2);
        }

        if (normA == 0 || normB == 0) {
            return 0.0;
        }

        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    }

    private String resolveName(CSVRecord record, Map<String, String> headers) {
        String name = resolveValue(record, headers, NAME_COLUMNS);
        if (StringUtils.hasText(name)) {
            return name.trim();
        }
        String first = resolveValue(record, headers, FIRST_NAME_COLUMNS);
        String last = resolveValue(record, headers, LAST_NAME_COLUMNS);
        if (StringUtils.hasText(first) || StringUtils.hasText(last)) {
            return (StringUtils.hasText(first) ? first.trim() : "") + " " + (StringUtils.hasText(last) ? last.trim() : "");
        }
        return null;
    }

    private String resolveValue(CSVRecord record, Map<String, String> headers, String[] candidates) {
        for (String candidate : candidates) {
            String normalized = candidate.toLowerCase(Locale.ROOT);
            if (headers.containsKey(normalized)) {
                String raw = record.get(headers.get(normalized));
                if (StringUtils.hasText(raw)) {
                    return raw.trim();
                }
            }
        }
        return null;
    }

    private List<String> parseTags(String tagsValue) {
        if (!StringUtils.hasText(tagsValue)) {
            return null;
        }
        String[] split = tagsValue.split("[,;]");
        return Arrays.stream(split)
                .map(String::trim)
                .filter(token -> !token.isEmpty())
                .collect(Collectors.toList());
    }

    private Integer parseInteger(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        try {
            return Integer.parseInt(value.trim());
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private NodeResponse mapToResponse(Node node) {
        return NodeResponse.builder()
                .id(node.getId())
                .type(node.getType())
                .name(node.getName())
                .description(node.getDescription())
                .sector(node.getSector())
                .tags(node.getTags())
                .relationshipStrength(node.getRelationshipStrength())
                .company(node.getCompany())
                .role(node.getRole())
                .linkedinUrl(node.getLinkedinUrl())
                .notes(node.getNotes())
                .priority(node.getPriority())
                .dueDate(node.getDueDate())
                .startDate(node.getStartDate())
                .endDate(node.getEndDate())
                .status(node.getStatus())
                .properties(node.getProperties())
                .createdAt(node.getCreatedAt())
                .updatedAt(node.getUpdatedAt())
                .build();
    }

    private void validateNodeRequest(NodeRequest nodeRequest) {
        if (nodeRequest == null) {
            throw new IllegalArgumentException("Node payload is required");
        }
        if (nodeRequest.getType() == null) {
            throw new IllegalArgumentException("Node type is required");
        }
        if (!StringUtils.hasText(nodeRequest.getName())) {
            throw new IllegalArgumentException("Node name is required");
        }
    }

    private List<String> normalizeTags(List<String> tags) {
        if (tags == null) {
            return new ArrayList<>();
        }
        return tags.stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(tag -> !tag.isEmpty())
                .collect(Collectors.toList());
    }

    private List<Double> generateEmbeddingForRequest(NodeRequest nodeRequest) {
        String payload = buildEmbeddingPayload(nodeRequest);
        if (payload == null || payload.isBlank()) {
            return null;
        }
        try {
            return embeddingService.generateEmbedding(payload);
        } catch (RuntimeException ex) {
            logger.warn("Embedding generation skipped for node '{}': {}", nodeRequest.getName(), ex.getMessage());
            return null;
        }
    }

    private String buildEmbeddingPayload(NodeRequest request) {
        StringBuilder builder = new StringBuilder();
        append(builder, request.getName());
        append(builder, request.getDescription());
        append(builder, request.getSector());
        if (request.getTags() != null) {
            request.getTags().forEach(tag -> append(builder, tag));
        }
        append(builder, request.getCompany());
        append(builder, request.getRole());
        append(builder, request.getNotes());
        if (request.getPriority() != null) {
            append(builder, String.valueOf(request.getPriority()));
        }
        if (request.getDueDate() != null) {
            append(builder, request.getDueDate().toString());
        }
        if (request.getStatus() != null) {
            append(builder, request.getStatus().name());
        }
        if (builder.length() == 0) {
            return null;
        }
        return builder.toString().trim();
    }

    private void append(StringBuilder builder, String value) {
        if (value == null) {
            return;
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            return;
        }
        builder.append(trimmed).append(" ");
    }

    private Specification<Node> belongsToUser(UUID userId) {
        return (root, query, builder) -> builder.equal(root.get("user").get("id"), userId);
    }

    private Specification<Node> hasType(NodeType type) {
        return (root, query, builder) -> builder.equal(root.get("type"), type);
    }

    private Specification<Node> hasAnyType(List<NodeType> types) {
        return (root, query, builder) -> root.get("type").in(types);
    }

    private Specification<Node> hasSector(String sector) {
        String normalized = sector.trim().toLowerCase(Locale.ROOT);
        return (root, query, builder) -> builder.equal(builder.lower(root.get("sector")), normalized);
    }

    private Specification<Node> hasAllTags(List<String> tags) {
        List<String> normalized = tags.stream()
                .filter(Objects::nonNull)
                .map(tag -> tag.trim().toLowerCase(Locale.ROOT))
                .filter(token -> !token.isEmpty())
                .collect(Collectors.toList());

        if (normalized.isEmpty()) {
            return null;
        }

        Specification<Node> specification = null;
        for (String tag : normalized) {
            Specification<Node> tagSpec = (root, query, builder) -> {
                Subquery<Integer> subquery = query.subquery(Integer.class);
                Root<Node> subRoot = subquery.from(Node.class);
                Join<Node, String> join = subRoot.join("tags", JoinType.INNER);
                subquery.select(builder.literal(1))
                        .where(builder.and(
                                builder.equal(subRoot.get("id"), root.get("id")),
                                builder.equal(builder.lower(join), tag)
                        ));
                return builder.exists(subquery);
            };
            specification = specification == null ? tagSpec : specification.and(tagSpec);
        }
        return specification;
    }

    private Specification<Node> hasMinRelationshipStrength(Integer min) {
        return (root, query, builder) -> builder.greaterThanOrEqualTo(root.get("relationshipStrength"), min);
    }

    private Specification<Node> hasMaxRelationshipStrength(Integer max) {
        return (root, query, builder) -> builder.lessThanOrEqualTo(root.get("relationshipStrength"), max);
    }

    private Specification<Node> containsSearchTerm(String searchTerm) {
        String normalized = searchTerm.trim().toLowerCase(Locale.ROOT);
        String pattern = "%" + normalized + "%";

        return (root, query, builder) -> {
            List<Predicate> predicates = new ArrayList<>();
            predicates.add(builder.like(builder.lower(root.get("name")), pattern));
            predicates.add(builder.like(builder.lower(root.get("description")), pattern));
            predicates.add(builder.like(builder.lower(root.get("sector")), pattern));
            predicates.add(builder.like(builder.lower(root.get("company")), pattern));
            predicates.add(builder.like(builder.lower(root.get("role")), pattern));
            predicates.add(builder.like(builder.lower(root.get("notes")), pattern));

            Predicate textPredicate = builder.or(predicates.toArray(new Predicate[0]));

            Subquery<Integer> tagSubquery = query.subquery(Integer.class);
            Root<Node> tagRoot = tagSubquery.from(Node.class);
            Join<Node, String> tagJoin = tagRoot.join("tags", JoinType.LEFT);
            tagSubquery.select(builder.literal(1))
                    .where(builder.and(
                            builder.equal(tagRoot.get("id"), root.get("id")),
                            builder.like(builder.lower(tagJoin), pattern)
                    ));

            return builder.or(textPredicate, builder.exists(tagSubquery));
        };
    }

    private record PathSearchState(UUID nodeId, List<UUID> path) {
    }
}
