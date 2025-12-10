package com.fahribilgen.networkcrm.service;

import java.util.List;

public interface EmbeddingService {
    List<Double> generateEmbedding(String text);
}
