package com.fahribilgen.networkcrm.entity;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;
import java.util.List;
import java.util.Map;

@Converter(autoApply = false)
public class JsonAttributeConverter implements AttributeConverter<Object, String> {
    private static final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public String convertToDatabaseColumn(Object attribute) {
        if (attribute == null) return null;
        try {
            return objectMapper.writeValueAsString(attribute);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("Could not serialize attribute to JSON", e);
        }
    }

    @Override
    public Object convertToEntityAttribute(String dbData) {
        if (dbData == null) return null;
        try {
            // Try to parse as Map first, fallback to List
            if (dbData.trim().startsWith("{")) {
                return objectMapper.readValue(dbData, Map.class);
            } else if (dbData.trim().startsWith("[")) {
                return objectMapper.readValue(dbData, List.class);
            } else {
                return dbData;
            }
        } catch (Exception e) {
            throw new IllegalArgumentException("Could not deserialize JSON to attribute", e);
        }
    }
}
