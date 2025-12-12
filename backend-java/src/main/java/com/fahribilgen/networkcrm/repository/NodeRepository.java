package com.fahribilgen.networkcrm.repository;

import java.util.List;
import java.util.UUID;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.stereotype.Repository;

import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.enums.NodeType;

@Repository
public interface NodeRepository extends JpaRepository<Node, UUID>, JpaSpecificationExecutor<Node> {

    List<Node> findByUserId(UUID userId);

    List<Node> findByUserId(UUID userId, Pageable pageable);

    List<Node> findByUserIdAndType(UUID userId, NodeType type);

    boolean existsByUserIdAndNameIgnoreCase(UUID userId, String name);
}
