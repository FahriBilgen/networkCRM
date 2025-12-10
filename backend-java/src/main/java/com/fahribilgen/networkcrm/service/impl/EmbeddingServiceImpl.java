package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.service.EmbeddingService;
import dev.langchain4j.data.embedding.Embedding;
import dev.langchain4j.model.embedding.EmbeddingModel;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class EmbeddingServiceImpl implements EmbeddingService {

    @Autowired
    private EmbeddingModel embeddingModel;

    @Override
    public List<Double> generateEmbedding(String text) {
        if (text == null || text.isEmpty()) {
            return null;
        }
        Embedding embedding = embeddingModel.embed(text).content();
        // Convert float[] to List<Double>
        return embedding.vectorAsList().stream()
                .map(Float::doubleValue)
                .collect(Collectors.toList());
    }
}
