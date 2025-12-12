package com.fahribilgen.networkcrm.repository;

import com.fahribilgen.networkcrm.entity.FavoritePath;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface FavoritePathRepository extends JpaRepository<FavoritePath, UUID> {
    List<FavoritePath> findByUserId(UUID userId);

    Optional<FavoritePath> findByIdAndUserId(UUID id, UUID userId);
}
