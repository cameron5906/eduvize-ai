import { Route, Routes, useMatch, useNavigate } from "react-router-dom";
import { UserProvider } from "@context/user";
import { useOnboarding } from "@context/user/hooks";
import { Profile } from "@views/profile";
import { Header } from "./sections";
import { SetupCta, VerificationCta } from "./cta";
import { ReactNode, useEffect } from "react";
import { Container } from "@mantine/core";
import { Courses } from "@views/courses";
import { Course } from "@views/course";

const CallToActionOrView = ({ children }: { children: React.ReactNode }) => {
    const isProfile = useMatch("/dashboard/profile");
    const { is_profile_complete, is_verified } = useOnboarding();

    let preCheckComponent: ReactNode | null = null;
    if (!is_verified) {
        preCheckComponent = <VerificationCta />;
    } else if (!is_profile_complete && !isProfile) {
        preCheckComponent = <SetupCta />;
    }

    if (preCheckComponent) {
        return (
            <Container size="md" p="xl">
                {preCheckComponent}
            </Container>
        );
    }

    return children;
};

export const Dashboard = () => {
    const navigate = useNavigate();
    const isDashboardRoot = useMatch("/dashboard");

    useEffect(() => {
        if (isDashboardRoot) {
            navigate("/dashboard/courses");
        }
    }, []);

    return (
        <UserProvider>
            <Header />

            <Routes>
                <Route
                    path="course/:course_id"
                    handle="course"
                    element={
                        <CallToActionOrView>
                            <Course />
                        </CallToActionOrView>
                    }
                />
                <Route
                    path="course/:course_id/lesson/:lesson_id"
                    handle="lesson"
                    element={
                        <CallToActionOrView>
                            <Course />
                        </CallToActionOrView>
                    }
                />
                <Route
                    path="courses/*"
                    handle="courses"
                    element={
                        <CallToActionOrView>
                            <Courses />
                        </CallToActionOrView>
                    }
                />
                <Route
                    path="profile"
                    handle="profile"
                    element={
                        <CallToActionOrView>
                            <Profile />
                        </CallToActionOrView>
                    }
                />
            </Routes>
        </UserProvider>
    );
};
