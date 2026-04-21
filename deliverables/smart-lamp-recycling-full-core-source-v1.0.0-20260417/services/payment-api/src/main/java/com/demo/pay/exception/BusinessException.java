package com.demo.pay.exception;

public class BusinessException extends RuntimeException {

    private final int httpStatus;
    private final String errorCode;

    public BusinessException(int httpStatus, String errorCode) {
        super(errorCode);
        this.httpStatus = httpStatus;
        this.errorCode = errorCode;
    }

    public int getHttpStatus() {
        return httpStatus;
    }

    public String getErrorCode() {
        return errorCode;
    }
}
