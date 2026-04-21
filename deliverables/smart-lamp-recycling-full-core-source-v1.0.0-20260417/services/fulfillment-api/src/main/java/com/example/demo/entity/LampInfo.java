package com.example.demo.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "lamps")
public class LampInfo {
    @Id
    private String sku;
    private String name;
    private String description;

    public LampInfo() {}

    public LampInfo(String sku, String name, String description) {
        this.sku = sku;
        this.name = name;
        this.description = description;
    }

    public String getSku() { return sku; }
    public void setSku(String sku) { this.sku = sku; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}