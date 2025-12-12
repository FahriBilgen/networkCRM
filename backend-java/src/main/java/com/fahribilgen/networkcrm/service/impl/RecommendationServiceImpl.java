package com.fahribilgen.networkcrm.service.impl;

import java.text.Normalizer;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ResponseStatusException;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.EdgeRequest;
import com.fahribilgen.networkcrm.payload.EdgeResponse;
import com.fahribilgen.networkcrm.payload.GoalNetworkDiagnosticsResponse;
import com.fahribilgen.networkcrm.payload.GoalSuggestionResponse;
import com.fahribilgen.networkcrm.payload.LinkPersonToGoalRequest;
import com.fahribilgen.networkcrm.payload.NodeClassificationRequest;
import com.fahribilgen.networkcrm.payload.NodeClassificationResponse;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.payload.NodeSectorSuggestionRequest;
import com.fahribilgen.networkcrm.payload.NodeSectorSuggestionResponse;
import com.fahribilgen.networkcrm.payload.RelationshipNudgeResponse;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.EdgeService;
import com.fahribilgen.networkcrm.service.EmbeddingService;
import com.fahribilgen.networkcrm.service.RecommendationService;

@Service
public class RecommendationServiceImpl implements RecommendationService {

    private static final Logger logger = LoggerFactory.getLogger(RecommendationServiceImpl.class);
    private static final List<String> VISION_KEYWORDS = List.of("vision", "vizyon", "north star", "mission", "purpose", "hayal", "dream", "uzun vade");
    private static final List<String> GOAL_KEYWORDS = List.of("goal", "hedef", "objective", "target", "okr", "metric", "deliverable");
    private static final List<String> PROJECT_KEYWORDS = List.of("project", "proje", "kampanya", "campaign", "sprint", "pilot", "build");
    private static final List<String> EXECUTION_WORDS = List.of("uygulama", "implementation", "insa", "delivery", "launch", "gelistir", "execute");
    private static final Map<String, List<String>> SECTOR_KEYWORDS;

    static {
        Map<String, List<String>> sectorMap = new LinkedHashMap<>();
        sectorMap.put("Fintech", List.of("fintech", "banking", "payments", "psd2", "finance", "pos", "lending"));
        sectorMap.put("SaaS", List.of("saas", "b2b", "subscription", "crm", "erp", "workflow", "automation"));
        sectorMap.put("HealthTech", List.of("health", "medical", "clinic", "patient", "wellness", "pharma", "biotech"));
        sectorMap.put("E-commerce", List.of("e-commerce", "marketplace", "retail", "shop", "merchant", "order", "fulfillment"));
        sectorMap.put("AI & Data", List.of("ai", "machine learning", "ml", "data", "analytics", "llm", "model"));
        sectorMap.put("Cybersecurity", List.of("security", "zero trust", "identity", "encryption", "threat", "sso"));
        sectorMap.put("Gaming", List.of("game", "gaming", "esports", "unity", "unreal", "metaverse"));
        sectorMap.put("Climate", List.of("climate", "carbon", "sustainability", "energy", "renewable", "ev"));
        SECTOR_KEYWORDS = sectorMap;
    }

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EdgeRepository edgeRepository;

    @Autowired
    private EdgeService edgeService;

    @Autowired
    private EmbeddingService embeddingService;

    @Override
    public GoalSuggestionResponse suggestPeopleForGoal(UUID goalId, int limit, User user) {
        Node goal = getNode(goalId);
        validateOwnership(goal, user);
        if (goal.getType() != NodeType.GOAL) {
            throw new RuntimeException("Node is not a goal");
        }

        ensureNodeEmbedding(goal);

        List<Node> people = nodeRepository.findByUserIdAndType(user.getId(), NodeType.PERSON);
        if (CollectionUtils.isEmpty(people)) {
            return GoalSuggestionResponse.builder()
                    .goalId(goalId)
                    .suggestions(List.of())
                    .build();
        }

        List<GoalSuggestionResponse.PersonSuggestion> suggestions = people.stream()
                .filter(person -> person.getEmbedding() != null)
                .map(person -> {
                    double score = cosineSimilarity(goal.getEmbedding(), person.getEmbedding());
                    String reason = "Yüksek anlamsal benzerlik";
                    if (goal.getSector() != null && !goal.getSector().isEmpty()
                            && goal.getSector().equalsIgnoreCase(person.getSector())) {
                        reason = "Ortak sektör (" + goal.getSector() + ") ve anlamsal uyum";
                    }
                    return GoalSuggestionResponse.PersonSuggestion.builder()
                            .person(mapToNodeResponse(person))
                            .score(score)
                            .reason(reason)
                            .build();
                })
                .filter(suggestion -> suggestion.getScore() > 0)
                .sorted(Comparator.comparingDouble(GoalSuggestionResponse.PersonSuggestion::getScore).reversed())
                .limit(Math.max(limit, 1))
                .collect(Collectors.toList());

        return GoalSuggestionResponse.builder()
                .goalId(goalId)
                .suggestions(suggestions)
                .build();
    }

    @Override
    @Transactional
    public EdgeResponse linkPersonToGoal(UUID goalId, LinkPersonToGoalRequest request, User user) {
        if (request.getPersonId() == null) {
            throw new RuntimeException("personId is required");
        }

        Node goal = getNode(goalId);
        Node person = getNode(request.getPersonId());

        validateOwnership(goal, user);
        validateOwnership(person, user);

        if (goal.getType() != NodeType.GOAL) {
            throw new RuntimeException("Target node is not a goal");
        }
        if (person.getType() != NodeType.PERSON) {
            throw new RuntimeException("Source node is not a person");
        }

        Optional<Edge> existing = edgeRepository.findFirstBySourceNodeIdAndTargetNodeIdAndType(person.getId(), goal.getId(), EdgeType.SUPPORTS);
        existing.ifPresent(edgeRepository::delete);

        EdgeRequest edgeRequest = new EdgeRequest();
        edgeRequest.setSourceNodeId(person.getId());
        edgeRequest.setTargetNodeId(goal.getId());
        edgeRequest.setType(EdgeType.SUPPORTS);
        edgeRequest.setWeight(request.getRelationshipStrength() == null ? 0 : request.getRelationshipStrength());
        edgeRequest.setRelevanceScore(request.getRelevanceScore());
        edgeRequest.setAddedByUser(request.getAddedByUser() == null ? Boolean.TRUE : request.getAddedByUser());
        edgeRequest.setNotes(request.getNotes());
        edgeRequest.setRelationshipStrength(request.getRelationshipStrength());

        return edgeService.createEdge(edgeRequest, user);
    }

    @Override
    public NodeClassificationResponse classifyNodeCandidate(NodeClassificationRequest request, User user) {
        if (request == null || !StringUtils.hasText(request.getName())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Isim alanA gerekli.");
        }

        EnumMap<NodeType, Double> scores = new EnumMap<>(NodeType.class);
        EnumMap<NodeType, List<String>> signalMap = new EnumMap<>(NodeType.class);
        scores.put(NodeType.VISION, scoreVision(request, signalMap));
        scores.put(NodeType.GOAL, scoreGoal(request, signalMap));
        scores.put(NodeType.PROJECT, scoreProject(request, signalMap));

        NodeType suggested = scores.entrySet().stream()
                .max(Comparator.comparingDouble(entry -> entry.getValue() == null ? 0 : entry.getValue()))
                .map(java.util.Map.Entry::getKey)
                .orElse(NodeType.GOAL);
        double bestScore = scores.getOrDefault(suggested, 0.0);
        double totalScore = scores.values().stream().mapToDouble(Double::doubleValue).sum();
        double confidence = totalScore <= 0 ? 0.0 : bestScore / totalScore;

        List<String> signals = signalMap.getOrDefault(suggested, List.of());
        String rationale = buildRationale(suggested, bestScore, confidence, signals);

        return NodeClassificationResponse.builder()
                .suggestedType(suggested)
                .confidence(confidence)
                .scores(scores)
                .matchedSignals(signals)
                .rationale(rationale)
                .build();
    }

    @Override
    public NodeSectorSuggestionResponse suggestSector(NodeSectorSuggestionRequest request, User user) {
        if (request == null || (!StringUtils.hasText(request.getName())
                && !StringUtils.hasText(request.getDescription())
                && !StringUtils.hasText(request.getNotes())
                && CollectionUtils.isEmpty(request.getTags()))) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Sektor onerisini hesaplamak icin temel veriler gerekli.");
        }

        StringBuilder corpusBuilder = new StringBuilder();
        append(corpusBuilder, request.getName());
        append(corpusBuilder, request.getDescription());
        append(corpusBuilder, request.getNotes());
        if (request.getTags() != null) {
            request.getTags().forEach(tag -> append(corpusBuilder, tag));
        }
        String corpus = normalizeText(corpusBuilder.toString());
        if (corpus.isBlank()) {
            return NodeSectorSuggestionResponse.builder()
                    .sector("Genel")
                    .confidence(0.0)
                    .matchedKeywords(List.of())
                    .rationale("Anahtar kelime bulunamadi.")
                    .build();
        }

        Map<String, Integer> counts = new LinkedHashMap<>();
        Map<String, List<String>> matched = new LinkedHashMap<>();
        int totalMatches = 0;

        for (Map.Entry<String, List<String>> entry : SECTOR_KEYWORDS.entrySet()) {
            int count = 0;
            List<String> hits = new java.util.ArrayList<>();
            for (String keyword : entry.getValue()) {
                String normalizedKeyword = normalizeText(keyword);
                if (normalizedKeyword.isBlank()) {
                    continue;
                }
                if (corpus.contains(normalizedKeyword)) {
                    count++;
                    hits.add(keyword);
                }
            }
            if (count > 0) {
                counts.put(entry.getKey(), count);
                matched.put(entry.getKey(), hits);
                totalMatches += count;
            }
        }

        if (counts.isEmpty()) {
            return NodeSectorSuggestionResponse.builder()
                    .sector("Genel")
                    .confidence(0.0)
                    .matchedKeywords(List.of())
                    .rationale("Sektor anahtar kelimesi bulunamadi; manuel giriniz.")
                    .build();
        }

        String bestSector = counts.entrySet().stream()
                .max(Comparator.comparingInt(Map.Entry::getValue))
                .map(Map.Entry::getKey)
                .orElse("Genel");
        double confidence = totalMatches == 0 ? 0.0 : (double) counts.get(bestSector) / totalMatches;
        List<String> signals = matched.getOrDefault(bestSector, List.of());
        String rationale = "Eslestirilen kelimeler: " + String.join(", ", signals);

        return NodeSectorSuggestionResponse.builder()
                .sector(bestSector)
                .confidence(confidence)
                .matchedKeywords(signals)
                .rationale(rationale)
                .build();
    }

    @Override
    @Transactional(readOnly = true)
    public GoalNetworkDiagnosticsResponse getGoalNetworkDiagnostics(UUID goalId, User user) {
        Node goal = getNode(goalId);
        validateOwnership(goal, user);
        if (goal.getType() != NodeType.GOAL) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Diagnostics only goal nodes icin desteklenir.");
        }

        List<Edge> edges = edgeRepository.findByTargetNodeId(goalId);
        List<SupportDetail> supportDetails = new ArrayList<>();
        for (Edge edge : edges) {
            if (edge.getType() != EdgeType.SUPPORTS) {
                continue;
            }
            Node person = edge.getSourceNode();
            if (person == null || person.getType() != NodeType.PERSON
                    || person.getUser() == null || !person.getUser().getId().equals(user.getId())) {
                continue;
            }
            supportDetails.add(new SupportDetail(person, edge, daysSince(edge.getLastInteractionDate())));
        }

        List<Node> userNodes = nodeRepository.findByUserId(user.getId());

        GoalNetworkDiagnosticsResponse.Readiness readiness = buildReadiness(supportDetails);
        List<String> sectorHighlights = buildSectorHighlights(userNodes, supportDetails);
        List<String> riskAlerts = buildRiskAlerts(supportDetails);

        return GoalNetworkDiagnosticsResponse.builder()
                .goalId(goalId)
                .readiness(readiness)
                .sectorHighlights(sectorHighlights)
                .riskAlerts(riskAlerts)
                .build();
    }

    @Override
    @Transactional(readOnly = true)
    public RelationshipNudgeResponse getRelationshipNudges(User user, int limit) {
        int targetLimit = limit <= 0 ? 5 : limit;
        List<Edge> edges = edgeRepository.findBySourceNode_User_Id(user.getId());
        List<RelationshipNudgeResponse.Nudge> nudges = new ArrayList<>();
        for (Edge edge : edges) {
            Node source = edge.getSourceNode();
            if (source == null || source.getType() != NodeType.PERSON
                    || source.getUser() == null || !source.getUser().getId().equals(user.getId())) {
                continue;
            }
            List<String> reasons = buildNudgeReasons(edge);
            if (reasons.isEmpty()) {
                continue;
            }
            String targetName = edge.getTargetNode() != null ? edge.getTargetNode().getName() : null;
            RelationshipNudgeResponse.Nudge nudge = RelationshipNudgeResponse.Nudge.builder()
                    .person(mapToNodeResponse(source))
                    .edgeType(edge.getType())
                    .lastInteractionDate(edge.getLastInteractionDate())
                    .relationshipStrength(edge.getRelationshipStrength())
                    .targetName(targetName)
                    .reasons(reasons)
                    .build();
            nudges.add(nudge);
        }

        nudges.sort(Comparator.<RelationshipNudgeResponse.Nudge>comparingInt(n -> n.getReasons().size())
                .thenComparing(n -> {
                    LocalDate last = n.getLastInteractionDate();
                    return last == null ? LocalDate.MIN : last;
                }).reversed());

        if (nudges.size() > targetLimit) {
            nudges = new ArrayList<>(nudges.subList(0, targetLimit));
        }

        return RelationshipNudgeResponse.builder()
                .nudges(nudges)
                .build();
    }

    private void ensureNodeEmbedding(Node node) {
        if (node.getEmbedding() != null) {
            return;
        }
        StringBuilder builder = new StringBuilder();
        append(builder, node.getName());
        append(builder, node.getDescription());
        append(builder, node.getNotes());
        String payload = builder.toString().trim();
        if (payload.isEmpty()) {
            return;
        }
        try {
            List<Double> embedding = embeddingService.generateEmbedding(payload);
            node.setEmbedding(embedding);
            nodeRepository.save(node);
        } catch (Exception ex) {
            logger.warn("Failed to refresh embedding for node {}: {}", node.getId(), ex.getMessage());
        }
    }

    private void append(StringBuilder builder, String value) {
        if (value == null) {
            return;
        }
        String trimmed = value.trim();
        if (!trimmed.isEmpty()) {
            builder.append(trimmed).append(" ");
        }
    }

    private Node getNode(UUID nodeId) {
        return nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found: " + nodeId));
    }

    private void validateOwnership(Node node, User user) {
        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node " + node.getId());
        }
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

    private NodeResponse mapToNodeResponse(Node node) {
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

    private double scoreVision(NodeClassificationRequest request, EnumMap<NodeType, List<String>> signalMap) {
        List<String> signals = new java.util.ArrayList<>();
        double score = 0.0;
        score += keywordScore(request.getName(), VISION_KEYWORDS, 2.0, signals, "Isimde vizyon anahtarA bulundu.");
        score += keywordScore(request.getDescription(), VISION_KEYWORDS, 1.25, signals, "AAAklamada vizyon benzeri ifadeler var.");
        if (StringUtils.hasText(request.getNotes()) && request.getNotes().toLowerCase(Locale.ROOT).contains("neden")) {
            signals.add("Notlar bAlA14mA14nde 'neden' vurgusu var.");
            score += 0.5;
        }
        if (request.getPriority() != null && request.getPriority() <= 2) {
            signals.add("DA14AYA14k Ancelik uzun vadeli vizyona iAYaret ediyor.");
            score += 0.35;
        }
        signalMap.put(NodeType.VISION, signals);
        return score;
    }

    private double scoreGoal(NodeClassificationRequest request, EnumMap<NodeType, List<String>> signalMap) {
        List<String> signals = new java.util.ArrayList<>();
        double score = 0.0;
        score += keywordScore(request.getName(), GOAL_KEYWORDS, 2.0, signals, "Isimde hedef anahtar kelimesi.");
        score += keywordScore(request.getDescription(), GOAL_KEYWORDS, 1.0, signals, "AAAklamada hedef anahtar kelimesi.");
        if (request.getDueDate() != null) {
            signals.add("Hedef iAin bitiAY tarihi belirtilmiAY.");
            score += 0.75;
        }
        if (request.getPriority() != null) {
            signals.add("Ancelik deAYeri girilmiAY.");
            score += 0.6;
        }
        if (hasNumericGoal(request.getDescription())) {
            signals.add("AAAklamada metrik/numara bulunuyor.");
            score += 0.5;
        }
        signalMap.put(NodeType.GOAL, signals);
        return score;
    }

    private double scoreProject(NodeClassificationRequest request, EnumMap<NodeType, List<String>> signalMap) {
        List<String> signals = new java.util.ArrayList<>();
        double score = 0.0;
        score += keywordScore(request.getName(), PROJECT_KEYWORDS, 2.0, signals, "Isimde proje/campaign anahtar kelimesi.");
        score += keywordScore(request.getDescription(), PROJECT_KEYWORDS, 1.0, signals, "AAAklamada proje anahtar kelimesi.");
        score += keywordScore(request.getDescription(), EXECUTION_WORDS, 0.75, signals, "AAAklamada uygulama/delivery kelimeleri var.");
        if (request.getStartDate() != null && request.getDueDate() != null) {
            signals.add("BaAYlangAA ve bitiAY tarihleri belirtilmiAY.");
            score += 0.85;
        }
        if (StringUtils.hasText(request.getStatus())) {
            signals.add("Durum alanA mevcut.");
            score += 0.5;
        }
        signalMap.put(NodeType.PROJECT, signals);
        return score;
    }

    private GoalNetworkDiagnosticsResponse.Readiness buildReadiness(List<SupportDetail> details) {
        int total = details.size();
        long strongCount = details.stream()
                .map(SupportDetail::edge)
                .map(Edge::getRelationshipStrength)
                .filter(Objects::nonNull)
                .filter(value -> value >= 4)
                .count();
        long freshCount = details.stream()
                .map(SupportDetail::daysSinceInteraction)
                .filter(Objects::nonNull)
                .filter(days -> days <= 45)
                .count();

        double readinessScore = total == 0 ? 0 : ((strongCount / (double) total) * 0.6 + (freshCount / (double) total) * 0.4);
        readinessScore = Math.round(readinessScore * 100.0) / 100.0;

        String level = "weak";
        String message = "Network zayif gorunuyor, baglantilari guclendir.";
        if (readinessScore >= 0.7 || strongCount >= 3) {
            level = "strong";
            message = "Bu hedef icin network hazir gorunuyor.";
        } else if (readinessScore >= 0.45) {
            level = "medium";
            message = "Ag sinirda, yeni guclu baglantilar eklemeye calisin.";
        }
        if (total == 0) {
            message = "Bu hedefe bagli kisi yok.";
        }

        List<String> summary = new ArrayList<>();
        summary.add(String.format("%d baglanti", total));
        summary.add(String.format("%d baglanti 4+ guce sahip", strongCount));
        summary.add(String.format("%d baglanti son 45 gunde temas kurdu", freshCount));
        if (total > 0 && total < 3) {
            summary.add("En az 3 destekci olmadan hedef riskli.");
        }

        return GoalNetworkDiagnosticsResponse.Readiness.builder()
                .level(level)
                .score(readinessScore)
                .message(message)
                .summary(summary)
                .build();
    }

    private List<String> buildSectorHighlights(List<Node> userNodes, List<SupportDetail> details) {
        Map<String, Long> covered = new LinkedHashMap<>();
        for (SupportDetail detail : details) {
            String sector = normalizeSector(detail.person().getSector());
            if (sector.isEmpty()) {
                continue;
            }
            covered.merge(sector, 1L, Long::sum);
        }

        List<String> highlights = new ArrayList<>();
        if (!covered.isEmpty()) {
            Map.Entry<String, Long> top = covered.entrySet().stream()
                    .max(Map.Entry.comparingByValue())
                    .orElse(null);
            if (top != null) {
                highlights.add(String.format("%d baglanti %s sektorunde.", top.getValue(), top.getKey()));
            }
        }

        Map<String, Long> overall = new LinkedHashMap<>();
        for (Node node : userNodes) {
            if (node.getType() != NodeType.PERSON) {
                continue;
            }
            String sector = normalizeSector(node.getSector());
            if (sector.isEmpty()) {
                continue;
            }
            overall.merge(sector, 1L, Long::sum);
        }

        List<String> uncovered = overall.entrySet().stream()
                .filter(entry -> !entry.getKey().isEmpty() && !covered.containsKey(entry.getKey()))
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .limit(3)
                .map(Map.Entry::getKey)
                .toList();
        if (!uncovered.isEmpty()) {
            highlights.add("Eksik sektorler: " + String.join(", ", uncovered));
        }
        if (highlights.isEmpty()) {
            highlights.add("Sektor dagilimini hesaplamak icin veri yok.");
        }
        return highlights;
    }

    private List<String> buildRiskAlerts(List<SupportDetail> details) {
        if (details.isEmpty()) {
            return List.of("Destekci yok, once kisi ekleyin.");
        }
        List<String> alerts = new ArrayList<>();

        details.stream()
                .filter(detail -> detail.daysSinceInteraction() != null && detail.daysSinceInteraction() > 60)
                .sorted((a, b) -> Long.compare(b.daysSinceInteraction(), a.daysSinceInteraction()))
                .limit(3)
                .forEach(detail -> alerts.add(String.format("%s ile %d gundur iletisim yok.",
                detail.person().getName(),
                detail.daysSinceInteraction())));

        details.stream()
                .filter(detail -> {
                    Integer strength = detail.edge().getRelationshipStrength();
                    return strength == null || strength < 3;
                })
                .limit(3)
                .forEach(detail -> alerts.add(String.format("%s icin iliski gucu %d/5 seviyesinde.",
                detail.person().getName(),
                detail.edge().getRelationshipStrength() == null ? 0 : detail.edge().getRelationshipStrength())));

        if (alerts.isEmpty()) {
            alerts.add("Kritik risk bulunmadi.");
        }
        return alerts;
    }

    private String normalizeSector(String value) {
        if (!StringUtils.hasText(value)) {
            return "";
        }
        return value.trim().toLowerCase(Locale.ROOT);
    }

    private Long daysSince(LocalDate date) {
        if (date == null) {
            return null;
        }
        return ChronoUnit.DAYS.between(date, LocalDate.now());
    }

    private record SupportDetail(Node person, Edge edge, Long daysSinceInteraction) {

    }

    private List<String> buildNudgeReasons(Edge edge) {
        List<String> reasons = new ArrayList<>();
        Long daysSinceInteraction = daysSince(edge.getLastInteractionDate());
        if (daysSinceInteraction == null) {
            reasons.add("Hic gorusme kaydi yok.");
        } else if (daysSinceInteraction > 60) {
            reasons.add(String.format("%d gundur iletisim yok.", daysSinceInteraction));
        }
        Integer strength = edge.getRelationshipStrength();
        if (strength == null || strength <= 2) {
            reasons.add(String.format("Iliski gucu %d/5 seviyesinde.", strength == null ? 0 : strength));
        }
        return reasons;
    }

    private double keywordScore(String value, List<String> keywords, double weight, List<String> signals, String message) {
        if (!StringUtils.hasText(value)) {
            return 0.0;
        }
        String lower = value.toLowerCase(Locale.ROOT);
        for (String keyword : keywords) {
            if (lower.contains(keyword)) {
                if (message != null) {
                    signals.add(message);
                }
                return weight;
            }
        }
        return 0.0;
    }

    private boolean hasNumericGoal(String description) {
        if (!StringUtils.hasText(description)) {
            return false;
        }
        return description.chars().anyMatch(Character::isDigit);
    }

    private String normalizeText(String input) {
        if (!StringUtils.hasText(input)) {
            return "";
        }
        String lower = input.toLowerCase(Locale.ROOT);
        String normalized = Normalizer.normalize(lower, Normalizer.Form.NFD);
        return normalized.replaceAll("\\p{InCombiningDiacriticalMarks}+", "");
    }

    private String buildRationale(NodeType suggestedType, double bestScore, double confidence, List<String> signals) {
        StringBuilder builder = new StringBuilder();
        builder.append("Anerilen tip: ").append(suggestedType.name()).append(" (");
        builder.append(String.format(Locale.ROOT, "%.0f%% gA14ven", confidence * 100)).append("). ");
        if (!signals.isEmpty()) {
            builder.append("EAYleAYen sinyaller: ").append(String.join(", ", signals)).append(".");
        } else {
            builder.append("Sinyal bulunamadA; varsayAlan davranAAY uygulandA.");
        }
        return builder.toString();
    }
}
